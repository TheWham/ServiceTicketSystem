const CURRENT_ROLES = new Set(['EMPLOYEE', 'ENGINEER', 'PLATFORM_ADMIN', 'KNOWLEDGE_ADMIN'])

export function requireCurrentIdentity(user) {
  if (!user?.user_id || !CURRENT_ROLES.has(user.role)) {
    const error = new Error('登录服务返回了不受支持的身份，请联系管理员检查服务连接。')
    error.code = 'INVALID_IDENTITY'
    throw error
  }
  if (user.status !== 'ACTIVE') {
    const error = new Error('此账号当前不可用，请联系管理员。')
    error.code = 'ACCOUNT_DISABLED'
    throw error
  }
  const { display_name, enabled, ...identity } = user
  return identity
}

export function requireCurrentAccounts(response) {
  if (!Array.isArray(response?.data)) throw new Error('账号列表响应不完整，请重试。')
  return { ...response, data: response.data.map(requireCurrentIdentity) }
}
