import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import { ApiError, buildAnalyzeUrl } from '../services/analysisApi'

const testDir = path.dirname(fileURLToPath(import.meta.url))

function readFrontendVercelConfig() {
  const vercelConfigPath = path.resolve(testDir, '../../vercel.json')
  return JSON.parse(fs.readFileSync(vercelConfigPath, 'utf-8'))
}

function collectSourceFiles(dirPath) {
  const entries = fs.readdirSync(dirPath, { withFileTypes: true })
  const files = []
  for (const entry of entries) {
    const fullPath = path.join(dirPath, entry.name)
    if (entry.isDirectory()) {
      if (entry.name === '__tests__') {
        continue
      }
      files.push(...collectSourceFiles(fullPath))
      continue
    }
    if (/\.(js|jsx|ts|tsx)$/.test(entry.name)) {
      files.push(fullPath)
    }
  }
  return files
}

describe('frontend deployment configuration', () => {
  it('fails clearly when VITE_API_BASE_URL is missing', () => {
    const previous = import.meta.env.VITE_API_BASE_URL
    delete import.meta.env.VITE_API_BASE_URL

    try {
      expect(() => buildAnalyzeUrl()).toThrow(ApiError)
      expect(() => buildAnalyzeUrl()).toThrow(
        'Frontend API base URL is not configured. Set VITE_API_BASE_URL in frontend/.env or in the frontend deployment environment.',
      )
    } finally {
      import.meta.env.VITE_API_BASE_URL = previous
    }
  })

  it('includes SPA rewrites for root and analysis in Vercel config', () => {
    const config = readFrontendVercelConfig()

    expect(config.rewrites).toEqual([
      { source: '/analysis', destination: '/index.html' },
      { source: '/', destination: '/index.html' },
    ])
  })

  it('does not reference backend Earth Engine secrets in frontend source', () => {
    const srcDir = path.resolve(testDir, '..')
    const contents = collectSourceFiles(srcDir)
      .map((filePath) => fs.readFileSync(filePath, 'utf-8'))
      .join('\n')

    expect(contents).not.toContain('GEE_SERVICE_ACCOUNT_JSON')
    expect(contents).not.toContain('GEE_SERVICE_ACCOUNT_EMAIL')
    expect(contents).not.toContain('GEE_PRIVATE_KEY_FILE')
  })
})
