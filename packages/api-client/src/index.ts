import { createAiResource } from './ai'
import { createAuthResource } from './auth'
import { createBusinessesResource, createLocationsResource } from './business'
import { createHttp, type ApiClientConfig } from './client'
import { createDiscountsResource } from './discount'
import { createMenuCategoriesResource, createMenuItemsResource, createModifierGroupsResource } from './menu'
import { createOrdersResource } from './order'
import { createPaymentsResource } from './payment'
import { createPrintersResource } from './printer'
import { createReportsResource } from './report'
import { createShiftsResource } from './shift'
import { createStaffResource } from './staff'
import { createTablesResource } from './table'

export type { ApiClientConfig } from './client'

export function createApiClient(config: ApiClientConfig) {
  const http = createHttp(config)

  return {
    auth: createAuthResource(http),
    businesses: createBusinessesResource(http),
    locations: createLocationsResource(http),
    menuCategories: createMenuCategoriesResource(http),
    menuItems: createMenuItemsResource(http),
    modifierGroups: createModifierGroupsResource(http),
    tables: createTablesResource(http),
    orders: createOrdersResource(http),
    payments: createPaymentsResource(http),
    printers: createPrintersResource(http),
    staff: createStaffResource(http),
    reports: createReportsResource(http),
    discounts: createDiscountsResource(http),
    shifts: createShiftsResource(http),
    ai: createAiResource(http),
  }
}

export type SmartServeApiClient = ReturnType<typeof createApiClient>

