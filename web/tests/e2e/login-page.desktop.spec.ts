import { expect, test } from '@playwright/test'

test('桌面端登录页收敛为居中的单卡控制台入口', async ({ page }) => {
	await page.goto('/login')
	await page.waitForLoadState('networkidle')

	const loginConsole = page.locator('.login-console')
	await expect(loginConsole).toHaveCount(1)
	await expect(page.locator('.login-console__brand')).toHaveCount(1)
	await expect(page.locator('.login-console__title')).toHaveText('登录签到平台')
	await expect(page.locator('.login-shell__intro')).toHaveCount(0)
	await expect(page.locator('.login-shell__feature')).toHaveCount(0)

	const boundingBox = await loginConsole.boundingBox()
	expect(boundingBox).not.toBeNull()
	if (!boundingBox) {
		throw new Error('login-console boundingBox is null')
	}

	const viewport = page.viewportSize()
	expect(viewport).not.toBeNull()
	if (!viewport) {
		throw new Error('viewport size is null')
	}

	const centerX = boundingBox.x + boundingBox.width / 2
	const centerY = boundingBox.y + boundingBox.height / 2

	expect(Math.abs(centerX - viewport.width / 2)).toBeLessThan(32)
	expect(Math.abs(centerY - viewport.height / 2)).toBeLessThan(40)
})
