'use client'

import { useTranslations } from 'next-intl'
import type { ActiveToolExecution } from '@/lib/hooks/useAuditStream'

interface LiveToolIndicatorProps {
  tools: ActiveToolExecution[]
}

// Known tool names that have translations
const KNOWN_TOOLS = new Set([
  'search_products',
  'search_database',
  'search_customers',
  'search_orders',
  'search_users',
  'get_product',
  'get_user',
  'get_order',
  'get_customer',
  'create_product',
  'create_order',
  'create_user',
  'update_product',
  'update_order',
  'update_user',
  'delete_product',
  'delete_order',
  'send_email',
  'send_message',
  'analyze_sentiment',
  'analyze_image',
  'generate_report',
  'calculate_price',
  'validate_data',
  'fetch_data',
  'process_payment',
  'check_inventory',
  'check_availability',
])

export function LiveToolIndicator({ tools }: LiveToolIndicatorProps) {
  const t = useTranslations('toolStatus')

  if (tools.length === 0) {
    return null
  }

  const getDisplayText = (tool: ActiveToolExecution): string => {
    if (tool.toolDescription) {
      return tool.toolDescription
    } else if (KNOWN_TOOLS.has(tool.toolName)) {
      return t(tool.toolName)
    } else {
      const readableToolName = tool.toolName.replace(/_/g, ' ')
      return t('executing', { toolName: readableToolName })
    }
  }

  return (
    <div className="space-y-2">
      {tools.map((tool) => {
        const key = `${tool.conversationId}-${tool.toolName}`
        const displayText = getDisplayText(tool)

        return (
          <div
            key={key}
            className="border-primary/20 bg-primary/5 animate-in fade-in slide-in-from-top-2 flex items-center gap-3 rounded-lg border px-4 py-3 text-sm"
          >
            <div className="flex items-center gap-1.5">
              <div className="bg-primary h-2 w-2 animate-pulse rounded-full" />
              <div
                className="bg-primary h-2 w-2 animate-pulse rounded-full"
                style={{ animationDelay: '0.2s' }}
              />
              <div
                className="bg-primary h-2 w-2 animate-pulse rounded-full"
                style={{ animationDelay: '0.4s' }}
              />
            </div>
            <div className="flex-1">
              <span className="text-foreground font-medium">{tool.agentName || 'Agent'}</span>
              <span className="text-muted-foreground mx-2">•</span>
              <span className="text-muted-foreground">{displayText}</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
