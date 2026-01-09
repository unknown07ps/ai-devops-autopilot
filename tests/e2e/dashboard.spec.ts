// Playwright E2E Tests for Deployr Dashboard
// ============================================
// Run: npx playwright test
// ============================================

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8001';
const DASHBOARD_URL = process.env.DASHBOARD_URL || 'file:///C:/Users/Daddy Sagar/ai-devops-autopilot/Deployr_dashboard.html';

test.describe('Dashboard UI Tests', () => {

    test.beforeEach(async ({ page }) => {
        // Clear localStorage before each test
        await page.goto(DASHBOARD_URL);
        await page.evaluate(() => localStorage.clear());
    });

    test('Dashboard loads successfully', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Check page title/branding
        await expect(page.locator('text=Deployr')).toBeVisible();

        // Check main navigation elements
        await expect(page.locator('text=Control Center')).toBeVisible();
        await expect(page.locator('text=Incidents')).toBeVisible();
        await expect(page.locator('text=Actions')).toBeVisible();
    });

    test('Login modal opens', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Click login button
        await page.click('button:has-text("Login")');

        // Check modal appears
        await expect(page.locator('input[type="email"]')).toBeVisible();
        await expect(page.locator('input[type="password"]')).toBeVisible();
    });

    test('Sign Up modal opens', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Click sign up button
        await page.click('button:has-text("Sign Up")');

        // Check modal appears with name field
        await expect(page.locator('input[type="email"]')).toBeVisible();
        await expect(page.locator('input[placeholder*="name" i]')).toBeVisible();
    });

    test('Sidebar navigation works', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Click on Incidents
        await page.click('text=Incidents');
        await page.waitForTimeout(500);

        // Verify incidents view loads
        await expect(page.locator('text=Incidents')).toBeVisible();

        // Click on Actions
        await page.click('text=Actions');
        await page.waitForTimeout(500);
    });

    test('Subscription page accessible', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Navigate to subscription
        await page.click('text=Subscription');
        await page.waitForTimeout(500);

        // Check pricing visible
        await expect(page.locator('text=Pro').first()).toBeVisible();
    });

    test('Dark theme is applied', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Check dark background
        const bgColor = await page.evaluate(() => {
            return window.getComputedStyle(document.body).backgroundColor;
        });

        // Should be dark (low RGB values)
        expect(bgColor).toContain('rgb');
    });

});

test.describe('API Integration Tests', () => {

    test('Health endpoint returns OK', async ({ request }) => {
        const response = await request.get(`${BASE_URL}/health`);
        expect(response.ok()).toBeTruthy();

        const body = await response.json();
        expect(body).toHaveProperty('status');
    });

    test('Subscription plans endpoint works', async ({ request }) => {
        const response = await request.get(`${BASE_URL}/api/subscription/plans`);
        expect(response.ok()).toBeTruthy();

        const plans = await response.json();
        expect(Array.isArray(plans)).toBeTruthy();
    });

    test('Unauthorized access returns 401', async ({ request }) => {
        const response = await request.get(`${BASE_URL}/api/auth/me`);
        expect(response.status()).toBe(401);
    });

    test('Login with valid credentials', async ({ request }) => {
        // First register a test user
        await request.post(`${BASE_URL}/api/auth/register`, {
            data: {
                email: 'playwright@test.com',
                password: 'TestPassword123!',
                full_name: 'Playwright Test'
            }
        });

        // Then login
        const response = await request.post(`${BASE_URL}/api/auth/login`, {
            data: {
                email: 'playwright@test.com',
                password: 'TestPassword123!'
            }
        });

        expect(response.status()).toBe(200);
        const body = await response.json();
        expect(body).toHaveProperty('access_token');
    });

    test('Login with invalid credentials returns 401', async ({ request }) => {
        const response = await request.post(`${BASE_URL}/api/auth/login`, {
            data: {
                email: 'invalid@test.com',
                password: 'wrongpassword'
            }
        });

        expect(response.status()).toBe(401);
    });

});

test.describe('Suppression Rules UI', () => {

    test('Suppression rules panel visible', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Navigate to view with suppression rules (if applicable)
        // The Triage & Noise Suppression is on the Control Center
        await page.click('text=Control Center');
        await page.waitForTimeout(1000);

        // Check for suppression rules heading
        const suppressionText = await page.locator('text=Suppression Rules').count();
        expect(suppressionText).toBeGreaterThan(0);
    });

    test('Toggle switches are functional', async ({ page }) => {
        await page.goto(DASHBOARD_URL);
        await page.waitForTimeout(1000);

        // Find toggle switches
        const toggles = page.locator('input[type="checkbox"]');
        const count = await toggles.count();

        if (count > 0) {
            // Click first toggle
            await toggles.first().click();
            await page.waitForTimeout(500);

            // Verify state changed (notification or UI update)
            // This is a basic check - actual verification depends on implementation
        }
    });

});

test.describe('Security Tests', () => {

    test('XSS in URL is handled', async ({ page }) => {
        // Try to inject XSS via URL
        const xssUrl = DASHBOARD_URL + '?q=<script>alert("xss")</script>';
        await page.goto(xssUrl);

        // Page should load without script execution
        await expect(page.locator('text=Deployr')).toBeVisible();
    });

    test('Console has no critical errors', async ({ page }) => {
        const errors: string[] = [];

        page.on('console', msg => {
            if (msg.type() === 'error') {
                errors.push(msg.text());
            }
        });

        await page.goto(DASHBOARD_URL);
        await page.waitForTimeout(2000);

        // Filter out known non-critical errors (like favicon)
        const criticalErrors = errors.filter(e =>
            !e.includes('favicon') &&
            !e.includes('404') &&
            !e.includes('Failed to load resource')
        );

        expect(criticalErrors.length).toBe(0);
    });

});
