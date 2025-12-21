import { Agent, IntegrationSource } from './types'
import { PLATFORM_TOOLS } from './platforms'

const lookerIntegration: IntegrationSource = {
  id: 'int-looker-1',
  agentId: 'agent-1',
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
  createdAt: '2024-12-15T10:00:00Z',
  updatedAt: '2024-12-19T14:30:00Z',
  availableTools: PLATFORM_TOOLS.looker || [],
}

const customApiIntegration: IntegrationSource = {
  id: 'int-custom-1',
  agentId: 'agent-1',
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
  createdAt: '2024-12-15T10:00:00Z',
  updatedAt: '2024-12-19T14:30:00Z',
  availableTools: [
    {
      id: 'custom-get-order',
      name: 'Get Order Status',
      description: 'Retrieve current order status',
      sourceId: 'int-custom-1',
    },
  ],
}

export const mockAgents: Agent[] = [
  {
    id: 'agent-1',
    userId: '550e8400-e29b-41d4-a716-446655440000',
    organizationId: '550e8400-e29b-41d4-a716-446655440001',
    name: 'Customer Support Agent',
    instructions: `You are a helpful and friendly customer support agent. Your role is to:

- Answer customer questions about orders and products
- Be polite and professional at all times
- If you cannot help, offer to connect them with a human agent
- Always check order status before providing information`,
    status: 'active',
    model_config: {
      provider: 'anthropic',
      model: 'claude-sonnet-4-5-20250929',
      temperature: 0.7,
      max_tokens: 4096,
    },
    createdAt: '2024-12-15T10:00:00Z',
    updatedAt: '2024-12-19T14:30:00Z',
    integrations: [lookerIntegration, customApiIntegration],
  },
  {
    id: 'agent-2',
    userId: '550e8400-e29b-41d4-a716-446655440000',
    organizationId: '550e8400-e29b-41d4-a716-446655440001',
    name: 'Sales Assistant',
    instructions: `You are a sales assistant helping customers find the right products. Your role is to:

- Understand customer needs and preferences
- Recommend products based on their requirements
- Check product availability before recommending
- Provide accurate pricing information`,
    status: 'inactive',
    model_config: {
      provider: 'openai',
      model: 'gpt-4o',
      temperature: 0.7,
      max_tokens: 4096,
    },
    createdAt: '2024-12-10T09:00:00Z',
    updatedAt: '2024-12-18T16:20:00Z',
    integrations: [],
  },
  {
    id: 'agent-3',
    userId: '550e8400-e29b-41d4-a716-446655440000',
    organizationId: '550e8400-e29b-41d4-a716-446655440001',
    name: 'Draft Agent',
    instructions: 'This is a draft agent being configured...',
    status: 'draft',
    model_config: {
      provider: 'google',
      model: 'gemini-2.0-flash-exp',
      temperature: 0.7,
      max_tokens: 4096,
    },
    createdAt: '2024-12-19T12:00:00Z',
    updatedAt: '2024-12-19T12:00:00Z',
    integrations: [],
  },
]
