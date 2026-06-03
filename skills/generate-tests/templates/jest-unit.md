# Jest Unit Test Templates

Reference templates for the `generate-tests` skill.

---

## Basic Function Test

```typescript
import { myFunction } from '../my-module';

describe('myFunction', () => {
  describe('when given valid input', () => {
    it('returns the expected result for a typical case', () => {
      // Arrange
      const input = 'example';
      const expected = 'EXAMPLE';

      // Act
      const result = myFunction(input);

      // Assert
      expect(result).toBe(expected);
    });
  });

  describe('edge cases', () => {
    it('handles empty string', () => {
      expect(myFunction('')).toBe('');
    });

    it('handles string with only whitespace', () => {
      expect(myFunction('   ')).toBe('');
    });
  });

  describe('error cases', () => {
    it('throws TypeError when given null', () => {
      expect(() => myFunction(null as unknown as string)).toThrow(TypeError);
    });

    it('throws with a descriptive message', () => {
      expect(() => myFunction(null as unknown as string))
        .toThrow('Input must be a non-null string');
    });
  });
});
```

---

## Async Function Test

```typescript
import { fetchUserById } from '../user.service';
import { db } from '../db';

// Module mock — mock the entire module
jest.mock('../db');
const mockDb = jest.mocked(db);

describe('fetchUserById', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('when the user exists', () => {
    it('returns the user', async () => {
      // Arrange
      const mockUser = { id: '123', name: 'Alice', email: 'alice@your-org.com' };
      mockDb.users.findById.mockResolvedValueOnce(mockUser);

      // Act
      const result = await fetchUserById('123');

      // Assert
      expect(result).toEqual(mockUser);
      expect(mockDb.users.findById).toHaveBeenCalledWith('123');
      expect(mockDb.users.findById).toHaveBeenCalledTimes(1);
    });
  });

  describe('when the user does not exist', () => {
    it('returns null', async () => {
      mockDb.users.findById.mockResolvedValueOnce(null);
      const result = await fetchUserById('999');
      expect(result).toBeNull();
    });
  });

  describe('when the database throws', () => {
    it('propagates the error', async () => {
      const dbError = new Error('Connection timeout');
      mockDb.users.findById.mockRejectedValueOnce(dbError);

      await expect(fetchUserById('123')).rejects.toThrow('Connection timeout');
    });
  });
});
```

---

## API Handler Test (Lambda)

```typescript
import { APIGatewayProxyEvent } from 'aws-lambda';
import { handler } from '../handler';
import { orderService } from '../order.service';

jest.mock('../order.service');
const mockOrderService = jest.mocked(orderService);

// Helper to build mock events
function makeEvent(overrides?: Partial<APIGatewayProxyEvent>): APIGatewayProxyEvent {
  return {
    httpMethod: 'POST',
    path: '/orders',
    body: JSON.stringify({ userId: 'user-123', items: [{ productId: 'prod-1', quantity: 2 }] }),
    headers: { 'Content-Type': 'application/json' },
    requestContext: { authorizer: { claims: { sub: 'user-123' } } },
    // ... other required fields
    ...overrides,
  } as APIGatewayProxyEvent;
}

describe('POST /orders handler', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('returns 201 with created order for valid request', async () => {
    const mockOrder = { id: 'order-1', status: 'pending' };
    mockOrderService.create.mockResolvedValueOnce(mockOrder);

    const response = await handler(makeEvent());

    expect(response.statusCode).toBe(201);
    expect(JSON.parse(response.body)).toEqual({ data: mockOrder });
  });

  it('returns 400 for missing required fields', async () => {
    const response = await handler(makeEvent({ body: '{}' }));

    expect(response.statusCode).toBe(400);
    expect(JSON.parse(response.body)).toMatchObject({ error: expect.any(String) });
  });

  it('returns 500 when service throws unexpected error', async () => {
    mockOrderService.create.mockRejectedValueOnce(new Error('DB timeout'));

    const response = await handler(makeEvent());

    expect(response.statusCode).toBe(500);
    // Must not expose internal error details
    expect(JSON.parse(response.body).error).not.toContain('DB timeout');
  });
});
```

---

## React Component Test

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OrderCard } from '../OrderCard';

const mockOrder = {
  id: 'order-123',
  status: 'pending' as const,
  total: 24.99,
  items: [{ name: 'Whopper', quantity: 1, price: 24.99 }],
};

describe('OrderCard', () => {
  it('renders order details', () => {
    render(<OrderCard order={mockOrder} />);

    expect(screen.getByText('order-123')).toBeInTheDocument();
    expect(screen.getByText('pending')).toBeInTheDocument();
    expect(screen.getByText('$24.99')).toBeInTheDocument();
  });

  it('calls onCancel when Cancel button is clicked', async () => {
    const mockOnCancel = jest.fn();
    const user = userEvent.setup();

    render(<OrderCard order={mockOrder} onCancel={mockOnCancel} />);

    await user.click(screen.getByRole('button', { name: /cancel/i }));

    expect(mockOnCancel).toHaveBeenCalledWith('order-123');
    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('does not render Cancel button for completed orders', () => {
    render(<OrderCard order={{ ...mockOrder, status: 'completed' }} />);

    expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument();
  });
});
```

---

## React Hook Test

```typescript
import { renderHook, act } from '@testing-library/react';
import { useCounter } from '../useCounter';

describe('useCounter', () => {
  it('initializes with the provided value', () => {
    const { result } = renderHook(() => useCounter(5));
    expect(result.current.count).toBe(5);
  });

  it('defaults to 0 when no initial value provided', () => {
    const { result } = renderHook(() => useCounter());
    expect(result.current.count).toBe(0);
  });

  it('increments count', () => {
    const { result } = renderHook(() => useCounter());

    act(() => {
      result.current.increment();
    });

    expect(result.current.count).toBe(1);
  });

  it('does not go below 0 on decrement', () => {
    const { result } = renderHook(() => useCounter(0));

    act(() => {
      result.current.decrement();
    });

    expect(result.current.count).toBe(0);
  });
});
```

---

## Mock Patterns

### MSW for HTTP Mocking
```typescript
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  http.get('/api/users/:id', ({ params }) => {
    return HttpResponse.json({ id: params.id, name: 'Test User' });
  }),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### Timer Mocks
```typescript
beforeEach(() => {
  jest.useFakeTimers();
});

afterEach(() => {
  jest.useRealTimers();
});

it('retries after delay', async () => {
  // ... setup
  jest.advanceTimersByTime(5000);
  await Promise.resolve(); // flush microtask queue
  // ... assert
});
```
