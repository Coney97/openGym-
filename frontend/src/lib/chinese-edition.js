import config from '../../chinese-edition.json'

export const CHINESE_EDITION = import.meta.env.VITE_ZH_CN_EDITION === '1'
export const CHINESE_CONFIG = config
export const APP_SCHEME = CHINESE_EDITION ? config.scheme : 'opengym'
