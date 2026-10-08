/**
 * 工单照片附件查看工具。
 * 后端 /attachments/{id}/content 需要 JWT，<img> 标签无法携带请求头，
 * 因此统一用 axios blob 拉取后生成 objectURL 供 el-image 展示/预览。
 */
import { attachmentApi } from '../api/index.js'

/** 按 attachment_id 列表逐个拉取照片，返回 objectURL 数组（加载失败的跳过） */
export async function loadPhotoUrls(attachmentIds) {
  const urls = []
  for (const id of attachmentIds || []) {
    try {
      const blob = await attachmentApi.fetchBlob(id)
      urls.push(URL.createObjectURL(blob))
    } catch (e) {
      console.error('[附件加载失败]', id, e?.message || e)
    }
  }
  return urls
}

/** 释放 objectURL，避免内存泄漏（弹窗重开/关闭前调用） */
export function revokePhotoUrls(urls) {
  ;(urls || []).forEach(u => URL.revokeObjectURL(u))
}
