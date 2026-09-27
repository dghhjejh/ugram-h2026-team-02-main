# Auto-Generated TypeScript Types from OpenAPI

This project uses **automatic type generation** from the FastAPI backend's OpenAPI schema to ensure type safety and prevent frontend-backend type mismatches.

## How It Works

1. **Backend** (FastAPI) automatically generates an OpenAPI schema at `/openapi.json`
2. **openapi-typescript** reads this schema and generates TypeScript types
3. **Frontend** imports these types for full type safety

## Generated Files

- `src/types/api-schema.ts` - **Auto-generated** (do not edit manually)
  - Contains all API paths, operations, and component schemas
  - Generated directly from the backend OpenAPI spec

- `src/types/api.ts` - **Type aliases** (manually maintained)
  - Re-exports commonly used types from `api-schema.ts`
  - Provides cleaner type names for easier use
  - Add custom types here for endpoints that return generic objects

## Usage

### Generating Types

Make sure the backend is running at `http://localhost:8001`, then run:

```bash
# Using npm scripts
npm run generate-types

# Or using Task
task fe:generate-types
```

### Watch Mode (Auto-regenerate on changes)

```bash
npm run generate-types:watch
```

### Using Types in Your Code

```typescript
import type { UserProfile, UserStats, ImagesResponse } from '../types/api';

// Types are now in sync with your backend!
const user: UserProfile = await apiClient.getUserProfile(userId);
const stats: UserStats = await apiClient.getUserStats(userId);
```

### Type-Safe API Client Example

```typescript
import type { components } from '../types/api-schema';

type CreateUserRequest = components['schemas']['CreateUserRequest'];

async function createUser(data: CreateUserRequest) {
  // TypeScript will ensure you pass all required fields
  const response = await fetch('/users', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  return response.json();
}
```

## When to Regenerate Types

Regenerate types whenever you:
- Add/modify/remove API endpoints in the backend
- Change request/response schemas
- Update Pydantic models in the backend

## Benefits

✅ **Type Safety** - Catch API mismatches at compile time, not runtime
✅ **Auto-completion** - Full IntelliSense for all API types
✅ **Single Source of Truth** - Backend defines the contract
✅ **No Manual Sync** - Types update automatically from OpenAPI schema
✅ **Documentation** - Types include JSDoc comments from backend

## Troubleshooting

**Error: "Failed to fetch OpenAPI schema"**
- Make sure the backend is running at `http://localhost:8001`
- Check that `/openapi.json` is accessible

**Types are outdated**
- Run `npm run generate-types` to regenerate
- Consider using watch mode during development
