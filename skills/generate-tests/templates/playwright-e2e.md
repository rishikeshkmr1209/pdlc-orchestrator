# Playwright E2E Test Templates

Reference templates for the `generate-tests` skill — E2E tests using the Page Object Model pattern.

---

## Directory Structure

```
e2e/
  tests/
    checkout.spec.ts
    login.spec.ts
    menu-browse.spec.ts
  pages/
    login.page.ts
    checkout.page.ts
    menu.page.ts
  fixtures/
    auth.fixture.ts       ← shared authenticated state
    test-data.ts          ← shared test constants
  playwright.config.ts
```

---

## Page Object Model

```typescript
// e2e/pages/login.page.ts
import { Page, Locator, expect } from '@playwright/test';

export class LoginPage {
  // Define all locators as class properties
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly errorAlert: Locator;
  readonly forgotPasswordLink: Locator;

  constructor(private readonly page: Page) {
    // Use accessible locators (role, label) — not CSS selectors
    this.emailInput = page.getByLabel('Email address');
    this.passwordInput = page.getByLabel('Password');
    this.submitButton = page.getByRole('button', { name: 'Sign in' });
    this.errorAlert = page.getByRole('alert');
    this.forgotPasswordLink = page.getByRole('link', { name: 'Forgot password?' });
  }

  async goto() {
    await this.page.goto('/login');
    await expect(this.submitButton).toBeVisible();
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }

  async expectErrorMessage(message: string) {
    await expect(this.errorAlert).toBeVisible();
    await expect(this.errorAlert).toHaveText(message);
  }
}
```

---

## Spec File

```typescript
// e2e/tests/login.spec.ts
import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/login.page';

test.describe('Login flow', () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
  });

  test('allows a registered user to sign in with valid credentials', async ({ page }) => {
    await loginPage.login(
      process.env.TEST_USER_EMAIL!,
      process.env.TEST_USER_PASSWORD!,
    );

    await expect(page).toHaveURL('/dashboard');
    await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
  });

  test('shows an error for incorrect password', async ({ page }) => {
    await loginPage.login('valid@example.com', 'wrong-password');

    await loginPage.expectErrorMessage('Invalid email or password');
    await expect(page).toHaveURL('/login'); // stays on login page
  });

  test('shows a validation error when email is empty', async ({ page }) => {
    await loginPage.login('', 'any-password');

    await expect(page.getByText('Email is required')).toBeVisible();
  });

  test('redirects to the originally requested page after login', async ({ page }) => {
    // Navigate to a protected page first
    await page.goto('/orders');
    // Should redirect to login
    await expect(page).toHaveURL('/login?redirect=%2Forders');

    await loginPage.login(
      process.env.TEST_USER_EMAIL!,
      process.env.TEST_USER_PASSWORD!,
    );

    // Should redirect back to original destination
    await expect(page).toHaveURL('/orders');
  });
});
```

---

## Auth Fixture (Shared Authenticated State)

```typescript
// e2e/fixtures/auth.fixture.ts
import { test as base, Page } from '@playwright/test';
import { LoginPage } from '../pages/login.page';

// Extend base test with an authenticated page
export const test = base.extend<{ authenticatedPage: Page }>({
  authenticatedPage: async ({ page }, use) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(
      process.env.TEST_USER_EMAIL!,
      process.env.TEST_USER_PASSWORD!,
    );
    await page.waitForURL('/dashboard');

    // Use storageState to reuse auth across tests (faster)
    await use(page);
  },
});

export { expect } from '@playwright/test';
```

Usage:
```typescript
// e2e/tests/orders.spec.ts
import { test, expect } from '../fixtures/auth.fixture';

test('shows the user orders list', async ({ authenticatedPage: page }) => {
  await page.goto('/orders');
  await expect(page.getByRole('heading', { name: 'Your Orders' })).toBeVisible();
});
```

---

## Playwright Config

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e/tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? 'github' : 'html',

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Add mobile viewports for responsive testing
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],

  // Start dev server for local runs
  webServer: process.env.CI ? undefined : {
    command: 'pnpm dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
  },
});
```

---

## Complex Flow Test (Multi-Page)

```typescript
// e2e/tests/checkout.spec.ts
import { test, expect } from '../fixtures/auth.fixture';
import { MenuPage } from '../pages/menu.page';
import { CartPage } from '../pages/cart.page';
import { CheckoutPage } from '../pages/checkout.page';
import { OrderConfirmationPage } from '../pages/order-confirmation.page';

test.describe('Checkout flow', () => {
  test('completes a full order from menu to confirmation', async ({ authenticatedPage: page }) => {
    const menu = new MenuPage(page);
    const cart = new CartPage(page);
    const checkout = new CheckoutPage(page);
    const confirmation = new OrderConfirmationPage(page);

    // Step 1: Browse menu and add item
    await menu.goto();
    await menu.addItemToCart('Whopper');
    await expect(cart.itemCount).toHaveText('1');

    // Step 2: View cart
    await cart.goto();
    await expect(cart.itemName('Whopper')).toBeVisible();
    await cart.proceedToCheckout();

    // Step 3: Complete checkout
    await expect(page).toHaveURL('/checkout');
    await checkout.selectPickupLocation('King St, Toronto');
    await checkout.confirmOrder();

    // Step 4: Verify confirmation
    await expect(page).toHaveURL(/\/orders\/[a-z0-9-]+/);
    await expect(confirmation.orderStatus).toHaveText('Order Confirmed');
    await expect(confirmation.estimatedTime).toBeVisible();
  });
});
```

---

## API Mock with Route Interception

```typescript
test('shows error state when order API fails', async ({ page }) => {
  // Intercept the API call and return an error
  await page.route('/api/orders', (route) => {
    route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'Internal server error' }),
    });
  });

  await page.goto('/orders');

  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.getByText('Unable to load orders')).toBeVisible();
});
```
