import { Agent, IntegrationSource, Conversation } from './types'
import { PLATFORM_TOOLS } from './platforms'

const lookerIntegration: IntegrationSource = {
  id: 'int-looker-1',
  name: 'Looker',
  type: 'platform',
  description: 'Analytics and business intelligence',
  icon: 'https://cdn.worldvectorlogo.com/logos/looker.svg',
  platformId: 'looker',
  config: {
    authConfig: {
      apiKeyValue: '••••••••',
    },
  },
  availableTools: PLATFORM_TOOLS.looker || [],
  enabledToolIds: ['looker-query-dashboard', 'looker-get-metrics'],
}

const customApiIntegration: IntegrationSource = {
  id: 'int-custom-1',
  name: 'Order Management API',
  type: 'custom-tool',
  description: 'Internal order tracking system',
  config: {
    endpoint: 'https://api.example.com/orders',
    method: 'GET',
    authentication: 'bearer',
    authConfig: {
      bearerToken: '••••••••',
    },
    parameters: [
      {
        id: 'param-1',
        name: 'orderId',
        type: 'string',
        required: true,
        description: 'Order ID to query',
      },
    ],
  },
  availableTools: [
    {
      id: 'custom-get-order',
      name: 'Get Order Status',
      description: 'Retrieve current order status',
      sourceId: 'int-custom-1',
    },
  ],
  enabledToolIds: ['custom-get-order'],
}

export const mockAgents: Agent[] = [
  {
    id: 'agent-1',
    name: 'Customer Support Agent',
    instructions: `You are a helpful and friendly customer support agent. Your role is to:

- Answer customer questions about orders and products
- Be polite and professional at all times
- If you cannot help, offer to connect them with a human agent
- Always check order status before providing information`,
    status: 'active',
    createdAt: '2024-12-15T10:00:00Z',
    updatedAt: '2024-12-19T14:30:00Z',
    integrations: [lookerIntegration, customApiIntegration],
  },
  {
    id: 'agent-2',
    name: 'Sales Assistant',
    instructions: `You are a sales assistant helping customers find the right products. Your role is to:

- Understand customer needs and preferences
- Recommend products based on their requirements
- Check product availability before recommending
- Provide accurate pricing information`,
    status: 'inactive',
    createdAt: '2024-12-10T09:00:00Z',
    updatedAt: '2024-12-18T16:20:00Z',
    integrations: [],
  },
  {
    id: 'agent-3',
    name: 'Draft Agent',
    instructions: 'This is a draft agent being configured...',
    status: 'draft',
    createdAt: '2024-12-19T12:00:00Z',
    updatedAt: '2024-12-19T12:00:00Z',
    integrations: [],
  },
]

export const mockConversations: Conversation[] = [
  {
    id: 'conv-1',
    agentId: 'agent-1',
    createdAt: '2024-12-19T15:30:00Z',
    messages: [
      {
        id: 'msg-1',
        role: 'user',
        content: 'Where is my order #12345?',
        timestamp: '2024-12-19T15:30:00Z',
      },
      {
        id: 'msg-2',
        role: 'agent',
        content: 'Let me check that for you...',
        toolCalls: [
          {
            toolId: 'tool-1',
            toolName: 'Get Order Status',
            input: { orderId: '12345' },
            output: { status: 'in_transit', estimatedDelivery: '2024-12-21' },
            success: true,
          },
        ],
        timestamp: '2024-12-19T15:30:05Z',
      },
      {
        id: 'msg-3',
        role: 'agent',
        content:
          'Your order #12345 is currently in transit and should arrive by December 21st, 2024.',
        timestamp: '2024-12-19T15:30:06Z',
      },
    ],
  },
]
