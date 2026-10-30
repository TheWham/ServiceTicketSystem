# -*- coding: utf-8 -*-
"""为 Neo4j 知识图谱节点注入 100% 纯中文语义标签体系 (Semantic Labels)。

将原先英文的标签全面汉化：
- :知识卡片 (原 Card，38个，紫色)
- :核心根因 (原 RootCause，62个，红色)
- :故障症状 (原 Fault，149个，粉色)
- :业务系统 (原 System，98个，蓝色)
- :处置动作 (原 Action，163个，绿色)
- :运维团队 (原 Team，13个，黄色)
- :实体     (原 Entity，455个，基础超类)

彻底清除英文标签，使得 Neo4j 浏览器侧边栏与节点全部显示纯正中文分类。
"""

import logging
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("enrich_neo4j_labels")


def enrich_labels(uri="bolt://localhost:7687", user="neo4j", password="neo4j123456"):
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        logger.info("开始为 Neo4j 节点注入纯中文语义标签...")

        # 1. 首先确保所有节点带有基础中文标签 :实体，并清除历史旧英文标签
        clean_and_base_queries = [
            "MATCH (n) SET n:实体",
            """
            MATCH (n) 
            REMOVE n:Action, n:Card, n:Entity, n:Fault, n:RootCause, n:System, n:Team
            """,
        ]
        for q in clean_and_base_queries:
            session.run(q)

        domain_queries = [
            # 1. 知识卡片 :知识卡片
            """
            MATCH (e:实体) 
            WHERE e.name STARTS WITH 'ITKB-'
            SET e:知识卡片
            """,
            
            # 2. 根因节点 :核心根因
            """
            MATCH (h:实体)-[:诱发根因]->(t:实体) 
            SET t:核心根因
            """,
            """
            MATCH (e:实体) 
            WHERE e.name CONTAINS '锁定' 
               OR e.name CONTAINS '轮询' 
               OR e.name CONTAINS '密码错误' 
               OR e.name CONTAINS '输错密码'
               OR e.name CONTAINS '根因'
            SET e:核心根因
            """,

            # 3. 故障异常与报错 :故障症状
            """
            MATCH (h:实体)-[:诱发根因]->(t:实体) 
            SET h:故障症状
            """,
            """
            MATCH (h:实体)-[:衍生次生故障]->(t:实体) 
            SET h:故障症状, t:故障症状
            """,
            """
            MATCH (e:实体) 
            WHERE e.name CONTAINS '错误' 
               OR e.name CONTAINS '失败' 
               OR e.name CONTAINS '691' 
               OR e.name CONTAINS '800' 
               OR e.name CONTAINS '809' 
               OR e.name CONTAINS '无法' 
               OR e.name CONTAINS '拒绝' 
               OR e.name CONTAINS '失效' 
               OR e.name CONTAINS '脱机' 
               OR e.name CONTAINS '死机' 
               OR e.name CONTAINS '蓝屏'
               OR e.name CONTAINS '异常'
            SET e:故障症状
            """,

            # 4. 处置排查动作 :处置动作
            """
            MATCH (h:实体)-[:处置动作]->(t:实体) 
            SET t:处置动作
            """,
            """
            MATCH (h:实体)-[:前置排查动作]->(t:实体) 
            SET t:处置动作
            """,
            """
            MATCH (e:实体) 
            WHERE e.name CONTAINS '排查' 
               OR e.name CONTAINS '重置' 
               OR e.name CONTAINS '解锁' 
               OR e.name CONTAINS '重启' 
               OR e.name CONTAINS '步骤' 
               OR e.name CONTAINS '动作'
               OR e.name CONTAINS '清理'
            SET e:处置动作
            """,

            # 5. 系统组件与资产 :业务系统
            """
            MATCH (h:实体)-[:依赖系统组件|依赖网络通道|依赖身份源]->(t:实体) 
            SET t:业务系统
            """,
            """
            MATCH (e:实体) 
            WHERE e.name CONTAINS 'VPN' 
               OR e.name CONTAINS 'AD域' 
               OR e.name CONTAINS '系统' 
               OR e.name CONTAINS '控制器' 
               OR e.name CONTAINS '打印机' 
               OR e.name CONTAINS 'Exchange' 
               OR e.name CONTAINS 'Outlook' 
               OR e.name CONTAINS 'MFA' 
               OR e.name CONTAINS 'RDP' 
               OR e.name CONTAINS 'DNS' 
               OR e.name CONTAINS '网关' 
               OR e.name CONTAINS 'Spooler'
               OR e.name CONTAINS '平台'
               OR e.name CONTAINS '客户端'
            SET e:业务系统
            """,

            # 6. 主责团队 :运维团队
            """
            MATCH (h:实体)-[:主责运维组]->(t:实体) 
            SET t:运维团队
            """,
            """
            MATCH (e:实体) 
            WHERE e.name CONTAINS '组' 
               OR e.name CONTAINS '部门' 
               OR e.name CONTAINS '支持'
            SET e:运维团队
            """,

            # 7. 规约状态 :规约状态
            """
            MATCH (e:实体) 
            WHERE e.name IN ['现行', '废止', '废弃', '草案', '生效'] 
            SET e:规约状态
            """,
        ]

        for q in domain_queries:
            session.run(q)

        logger.info("纯中文语义标签注入完成！当前标签分布：")
        labels_res = session.run("CALL db.labels() YIELD label RETURN label ORDER BY label")
        for r in labels_res:
            lbl = r["label"]
            cnt = session.run(f"MATCH (n:`{lbl}`) RETURN count(n) AS c").single()["c"]
            logger.info("  🏷️  :%s -> %d 个节点", lbl, cnt)

    driver.close()


if __name__ == "__main__":
    enrich_labels()
