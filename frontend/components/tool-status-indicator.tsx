'use client'

import { useTranslations } from 'next-intl'

interface ToolStatusIndicatorProps {
  toolName: string
  toolDescription: string | null
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

export function ToolStatusIndicator({ toolName, toolDescription }: ToolStatusIndicatorProps) {
  const t = useTranslations('toolStatus')

  // Priority: 1) tool_description from backend, 2) translated tool name, 3) generic fallback
  let displayText: string

  if (toolDescription) {
    displayText = toolDescription
  } else if (KNOWN_TOOLS.has(toolName)) {
    // Use specific translation for known tools
    displayText = t(toolName)
  } else {
    // Fallback to generic "executing" message with readable tool name
    const readableToolName = toolName.replace(/_/g, ' ')
    displayText = t('executing', { toolName: readableToolName })
  }

  return (
    <div className="bg-muted/50 text-muted-foreground flex items-center gap-3 rounded-lg px-4 py-3 text-sm">
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
      <span>{displayText}</span>
    </div>
  )
}
