import { dirname } from 'path'
import { fileURLToPath } from 'url'
import { nextConfig } from '@smartserve/config/eslint'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

export default nextConfig(__dirname)
