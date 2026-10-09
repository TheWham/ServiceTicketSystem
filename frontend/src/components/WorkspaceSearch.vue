<script setup>
// shadcn-vue Dialog composition, adapted with Reka UI accessibility primitives.
// https://www.shadcn-vue.com/docs/components/dialog
import { computed, ref, watch, nextTick } from 'vue'
import { DialogRoot, DialogPortal, DialogOverlay, DialogContent, DialogTitle, DialogDescription, DialogClose } from 'reka-ui'
import { Search, Close, Right } from '@element-plus/icons-vue'
const props = defineProps({ modelValue: Boolean, items: { type: Array, default: () => [] } })
const emit = defineEmits(['update:modelValue', 'select'])
const query = ref('')
const selected = ref(0)
const input = ref(null)
const filtered = computed(() => props.items.filter(item => `${item.label} ${item.description} ${item.keywords}`.toLowerCase().includes(query.value.trim().toLowerCase())))
watch(query, () => { selected.value = 0 })
watch(() => props.modelValue, async open => { if (open) { query.value = ''; selected.value = 0; await nextTick(); input.value?.focus() } })
function choose(item) { if (item) { emit('update:modelValue', false); emit('select', item.id) } }
function move(delta) { const count = filtered.value.length; if (count) selected.value = (selected.value + delta + count) % count }
function onKeydown(event) {
  if (event.isComposing || event.keyCode === 229) return
  if (!['ArrowDown', 'ArrowUp', 'Enter'].includes(event.key)) return
  event.preventDefault()
  if (event.key === 'Enter') choose(filtered.value[selected.value])
  else move(event.key === 'ArrowDown' ? 1 : -1)
}
</script>
<template>
  <DialogRoot :open="modelValue" @update:open="emit('update:modelValue', $event)">
    <DialogPortal>
      <DialogOverlay class="command-overlay" />
      <DialogContent class="command-dialog" @open-auto-focus.prevent="input?.focus()">
        <DialogTitle class="sr-only">快速前往</DialogTitle>
        <DialogDescription class="sr-only">搜索页面和常用操作，使用上下方向键选择，回车打开。</DialogDescription>
        <div class="command-input-wrap"><el-icon><Search /></el-icon><input ref="input" v-model="query" aria-label="搜索页面和操作" placeholder="想去哪里？搜索页面和操作…" role="combobox" aria-controls="workspace-results" aria-expanded="true" :aria-activedescendant="filtered.length ? `workspace-result-${selected}` : undefined" autocomplete="off" @keydown="onKeydown" /><DialogClose class="command-close" aria-label="关闭快速前往"><el-icon><Close /></el-icon></DialogClose></div>
        <p class="command-group-label">页面与操作</p>
        <div id="workspace-results" role="listbox" class="command-results" aria-label="搜索结果">
          <div v-for="(item, index) in filtered" :id="`workspace-result-${index}`" :key="item.id" role="option" :aria-selected="selected === index" class="command-option" @pointermove="selected = index" @click="choose(item)"><span><strong>{{ item.label }}</strong><small>{{ item.description }}</small></span><el-icon><Right /></el-icon></div>
          <div v-if="!filtered.length" class="command-empty" role="status">没有找到相关页面，换个关键词试试。</div>
        </div>
        <div class="command-footer"><span><kbd>↑</kbd><kbd>↓</kbd> 选择 <kbd>↵</kbd> 前往</span><span><kbd>Esc</kbd> 关闭</span></div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
