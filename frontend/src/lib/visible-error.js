import { t } from './i18n-core.js'
import { CHINESE_EDITION } from './chinese-edition.js'

// Remote servers can send arbitrary English diagnostics. Keep those on error.data for
// support/code-based handling; the dedicated edition shows a localized, actionable message.
export function visibleError(message, status = 0) {
  if (!CHINESE_EDITION) return message
  if (typeof message === 'string' && message) {
    const translated = t(message)
    if (translated !== message || /[\u3400-\u9fff]/.test(message)) return translated
  }
  const key = {
    400: 'The request was not accepted. Check the entered information.',
    401: 'Sign in or pair this device to continue.',
    403: 'You do not have permission to perform this action.',
    404: 'The requested item could not be found.',
    409: 'The operation conflicts with the current state. Refresh and try again.',
    413: 'The request is too large. Reduce its size and try again.',
    429: 'Too many requests. Wait a moment and try again.',
  }[status]
  if (key) return t(key)
  if (status >= 500) return t('The server could not complete the request. Try again later.')
  return t('The operation failed. Check the connection and configuration, then try again.')
}
