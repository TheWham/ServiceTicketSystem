package com.itticket.consultation.adapter.model;

import java.util.function.Consumer;

/**
 * 从模型流式输出的六键 JSON 文本中增量提取 {@code answerText} 字符串值。
 *
 * <p>设计约束(见 docs/superpowers/specs/2026-11-04-ai-chat-streaming-design.md):
 * <ul>
 *   <li>键序不依赖——answerText 出现之前缓冲扫描,出现即开始外发,不得依赖 system prompt
 *       中的示例键序;</li>
 *   <li>以 JSON 字符串语法状态机驱动(在字符串内/外、深度、转义),而非子串扫描——
 *       其他字符串值中出现 "answerText" 字样不得误触发;</li>
 *   <li>JSON 字符串转义(引号、反斜杠、斜杠、控制字符与四位十六进制形式)跨 chunk 边界正确解码,
 *       不完整的转义在缓冲中等待后续 chunk 补全后才外发;</li>
 *   <li>重复 answerText 取首个;answer 字符串值结束后即封口,后续输入不再消费
 *       (完整 JSON 的六键整校验由调用方对全文另行执行,流式只影响外发时机)。</li>
 * </ul>
 *
 * <p>本类只解决「边流边发的字是否正确」,不校验整个文档的合法性——模型若输出畸形 JSON,
 * 最终全文校验会以 {@code DependencyFailure.invalid()} 拒绝,已外发的暂定 token 由
 * 终审回滚协议(检 error/final 事件)处理。
 */
public final class StreamingJsonExtractor {

    private enum Phase {
        /** 尚未进入根对象。 */
        BEFORE_ROOT,
        /** 根对象内,结构化扫描(键识别 + 答案定位)。 */
        SCAN,
        /** 正在读取 answerText 的字符串值。 */
        ANSWER_VALUE,
        /** answerText 已封口,丢弃后续一切。 */
        DONE
    }

    private final Consumer<String> sink;

    private Phase phase = Phase.BEFORE_ROOT;
    private int depth = 0;
    private boolean inString = false;
    private boolean escaped = false;

    /** 深度 1 处于「期待键」位置(紧随 { 或 , 之后)。 */
    private boolean expectingKey = false;
    /** 深度 1 的键内容(仅 key 位置字符串收集)。 */
    private final StringBuilder keyBuffer = new StringBuilder();
    private boolean collectingKey = false;
    /** 刚闭合的深度 1 字符串是 "answerText",等冒号。 */
    private boolean awaitingColon = false;

    /** 答案外发缓冲:转义补全后才整段递交 sink,保证跨 chunk 转义正确。 */
    private final StringBuilder emitBuffer = new StringBuilder();
    /** 不完整的转义序列(如跨 chunk 的 "\uD83D"),补全后处理。 */
    private final StringBuilder pendingEscape = new StringBuilder();
    private boolean answerEscapePending = false;

    public StreamingJsonExtractor(Consumer<String> sink) {
        this.sink = sink;
    }

    /** 喂入一段模型流式增量(chunk 边界任意)。 */
    public void feed(String chunk) {
        if (chunk == null || chunk.isEmpty() || phase == Phase.DONE) {
            return;
        }
        final int n = chunk.length();
        for (int i = 0; i < n; i++) {
            char c = chunk.charAt(i);
            switch (phase) {
                case BEFORE_ROOT -> beforeRoot(c);
                case SCAN -> scan(c);
                case ANSWER_VALUE -> answerValue(c);
                case DONE -> { return; }
            }
        }
        flushAnswer();
    }

    private void beforeRoot(char c) {
        if (c == '{') {
            depth = 1;
            expectingKey = true;
            phase = Phase.SCAN;
        }
        // 根对象前的空白/垃圾:六键整校验兜底,这里只找根对象开头。
    }

    private void scan(char c) {
        if (inString) {
            if (escaped) {
                escaped = false;
                if (collectingKey) keyBuffer.append(unescapeChar(c));
            } else if (c == '\\') {
                escaped = true;
            } else if (c == '"') {
                inString = false;
                endString(String.valueOf(keyBuffer));
            } else if (collectingKey) {
                keyBuffer.append(c);
            }
            return;
        }
        // Mi1(2026-11-05 评审): answerText 值不是字符串(null/true/数字/数组/对象)时,
        // 终止流式外发——否则后续键名(如 "confidence")会被当作答案文本流出。
        // 非法载荷仍由终帧六键校验拒绝,这里只避免流式放大故障。
        if (depth == 1 && MARK_ANSWER.equals(keyBuffer.toString())
                && c != '"' && !Character.isWhitespace(c)) {
            phase = Phase.DONE;
            return;
        }
        switch (c) {
            case '"' -> {
                if (depth == 1 && MARK_ANSWER.equals(keyBuffer.toString())) {
                    // answerText 键冒号后的首个引号:进入答案值流式外发。
                    keyBuffer.setLength(0);
                    inString = true;
                    phase = Phase.ANSWER_VALUE;
                } else {
                    inString = true;
                    collectingKey = expectingKey && depth == 1;
                    if (collectingKey) {
                        keyBuffer.setLength(0);
                    }
                }
            }
            case '{', '[' -> depth++;
            case '}', ']' -> {
                depth--;
                if (depth == 0) {
                    // 根对象结束,answerText 若存在早已封口;未出现则保持扫描态丢弃尾缀。
                    phase = Phase.DONE;
                }
            }
            case ',' -> {
                if (depth == 1) expectingKey = true;
            }
            case ':' -> {
                if (depth == 1) {
                    if (awaitingColon) {
                        // 下一个非转义引号开启答案值;由 scan 继续,遇 '"' 且 depth==1 → 进入 ANSWER_VALUE
                        awaitingColon = false;
                        expectingKey = false;
                        keyBuffer.setLength(0);
                        keyBuffer.append(MARK_ANSWER);
                    } else {
                        expectingKey = false;
                    }
                }
            }
            default -> { /* 空白/数字/布尔等:结构上无关 */ }
        }
        // 进入答案值的时机:冒号后首个 '"'。上面 ':' 分支已做了标记,这里处理字符串开启。
    }

    /** depth==1 的 key 位字符串关闭时判定是否目标键;MARK 处理冒号后的答案引号。 */
    private static final String MARK_ANSWER = "\u0000answer";
    private static final String KEY_ANSWER = "answerText";

    private void endString(String content) {
        collectingKey = false;
        if (KEY_ANSWER.equals(content) && depth == 1) {
            awaitingColon = true;
        }
        // 非答案键:无视。
        // depth>1 的字符串:结构消费已由 inString 状态完成,无需额外处理。
    }

    //答案串开启的桥接:scan 的 ':' 分支把 keyBuffer 置为 MARK_ANSWER,
    //下一个 '"' 到来时若 keyBuffer 恰为 MARK_ANSWER 则切换 ANSWer_VALUE。
    //该方法由 scan::case '"' 逻辑调用。

    private void answerValue(char c) {
        if (answerEscapePending) {
            pendingEscape.append(c);
            if (pendingEscape.length() == 4) {
                String hex = pendingEscape.toString();
                pendingEscape.setLength(0);
                answerEscapePending = false;
                try {
                    emitBuffer.append((char) Integer.parseInt(hex, 16));
                } catch (NumberFormatException invalid) {
                    // 畸形四位十六进制转义:原样保留,交全文整校验拒绝,不因流式放大故障。
                    emitBuffer.append('\\').append('u').append(hex);
                }
            }
            return;
        }
        if (inString) {
            if (escaped) {
                escaped = false;
                switch (c) {
                    case '"', '\\', '/' -> emitBuffer.append(c);
                    case 'b' -> emitBuffer.append('\b');
                    case 'f' -> emitBuffer.append('\f');
                    case 'n' -> emitBuffer.append('\n');
                    case 'r' -> emitBuffer.append('\r');
                    case 't' -> emitBuffer.append('\t');
                    case 'u' -> {
                        answerEscapePending = true;
                        pendingEscape.setLength(0);
                    }
                    default -> {
                        // 非法转义:保留字面,交整校验拒绝。
                        emitBuffer.append('\\').append(c);
                    }
                }
            } else if (c == '\\') {
                escaped = true;
            } else if (c == '"') {
                inString = false;
                phase = Phase.DONE;
                flushAnswer();
            } else {
                emitBuffer.append(c);
            }
        } else {
            // 答案串外(胡乱插入的字符):忽略,整校验兜底。
        }
    }

    private char unescapeChar(char c) {
        return switch (c) {
            case 'n' -> '\n';
            case 't' -> '\t';
            case 'r' -> '\r';
            case 'b' -> '\b';
            case 'f' -> '\f';
            default -> c; // \" \\ \/ 与未知转义在键名中按字面保留
        };
    }

    /** 把已补全的缓冲整段递交 sink;不完整转义留在 pending 中等下个 chunk。 */
    private void flushAnswer() {
        if (emitBuffer.length() > 0) {
            sink.accept(emitBuffer.toString());
            emitBuffer.setLength(0);
        }
    }
}
