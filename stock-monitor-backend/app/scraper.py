"""
核心抓取引擎 — 使用 Playwright 模拟浏览器访问商品页面
移植自 stock-monitor/js/content.js 的 DOM 操作逻辑
"""
import asyncio
import logging
from playwright.async_api import async_playwright, Page, BrowserContext

from app.config import SCRAPE_TIMEOUT, SCRAPE_DELAY, MAX_RETRIES

logger = logging.getLogger(__name__)


async def scrape_all_products(products: list[dict]) -> list[dict]:
    """
    主入口：抓取所有商品的库存。
    返回: [{item_code, name, stocks: [{variant, in_stock}], error}]
    """
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="ja-JP",
        )

        for i, product in enumerate(products):
            logger.info(f"[{i+1}/{len(products)}] 正在检查: {product['name']}")
            result = await _scrape_single(context, product)
            results.append(result)
            # 商品之间的礼貌延迟
            await asyncio.sleep(SCRAPE_DELAY)

        await browser.close()

    return results


async def _scrape_single(context: BrowserContext, product: dict) -> dict:
    """
    抓取单个商品页面。
    返回: {item_code, name, stocks, error}
    """
    page = await context.new_page()

    try:
        # 导航到商品页面
        await page.goto(
            product["url"],
            wait_until="domcontentloaded",
            timeout=SCRAPE_TIMEOUT * 1000,
        )

        # 处理年龄验证弹窗
        await _dismiss_age_verification(page)

        # 等待变体列表出现
        try:
            await page.wait_for_selector(".variation_list", timeout=10000)
        except Exception:
            # 如果找不到变体列表，可能被年龄验证挡住了，再试一次
            await _dismiss_age_verification(page)
            await page.wait_for_selector(".variation_list", timeout=10000)

        # 提取商品名称
        name = await _extract_product_name(page, product.get("name", "未知商品"))

        # 提取库存变体
        stocks = await _extract_variants(page)

        return {
            "item_code": product["item_code"],
            "name": name,
            "stocks": stocks,
            "error": None if stocks else "未找到规格列表",
        }

    except Exception as e:
        logger.error(f"抓取失败 {product['name']}: {e}")
        return {
            "item_code": product["item_code"],
            "name": product.get("name", "未知商品"),
            "stocks": [],
            "error": str(e),
        }

    finally:
        await page.close()


async def _dismiss_age_verification(page: Page):
    """
    关闭年龄验证弹窗。
    策略：多个选择器依次尝试，兼容 content.js 的逻辑。
    """
    # 等待弹窗渲染
    await page.wait_for_timeout(1500)

    # 策略 1：自动接受任何 JS 弹窗
    page.on("dialog", lambda d: d.accept())

    # 策略 2：点击 "ENTER" / "入口" / "18歳以上" 按钮
    enter_selectors = [
        'a:has-text("ENTER")',
        'button:has-text("ENTER")',
        'a:has-text("入口")',
        'a:has-text("18歳以上")',
        "#splash a",
        ".splash a:first-child",
    ]

    for sel in enter_selectors:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=1000):
                await btn.click()
                await page.wait_for_timeout(1000)
                logger.info("年龄验证弹窗已关闭（点击按钮）")
                return
        except Exception:
            continue

    # 策略 3：通过 JS 直接移除弹窗元素
    try:
        await page.evaluate("""
            () => {
                const els = document.querySelectorAll('#splash, .splash, #age-verification, .age-verification, #simplemodal-data, #simplemodal-overlay');
                els.forEach(el => el.remove());
                // 恢复页面滚动
                document.body.style.overflow = '';
                document.documentElement.style.overflow = '';
            }
        """)
        logger.info("年龄验证弹窗已关闭（JS 移除）")
    except Exception as e:
        logger.warning(f"JS 移除弹窗失败: {e}")


async def _extract_product_name(page: Page, fallback: str) -> str:
    """从 h1 或 title 提取商品名称，与 content.js 逻辑一致"""
    try:
        h1 = page.locator("h1").first
        if await h1.is_visible():
            text = (await h1.text_content()).strip()
            if 0 < len(text) < 200:
                # 去除网站后缀 " - オナホ通販｜大人のおもちゃ通販大魔王" 等
                for sep in [" - オナホ通販", " - 大魔王", "｜", " - "]:
                    if sep in text:
                        text = text.split(sep)[0].strip()
                return text
    except Exception:
        pass

    try:
        title = await page.title()
        name = title.split(" - ")[0].strip()
        return name
    except Exception:
        pass

    return fallback


async def _extract_variants(page: Page) -> list[dict]:
    """
    从 .variation_list 容器中读取所有规格的库存状态。
    直接移植自 content.js 的 getVariantsFromList()。
    """
    stocks = []
    items = page.locator(".variation_list li")
    count = await items.count()

    for i in range(count):
        item = items.nth(i)
        data_type = await item.get_attribute("data-type") or ""
        class_name = await item.get_attribute("class") or ""

        variant_name = _map_variant_name(data_type)
        in_stock = "zero" not in class_name

        stocks.append({
            "variant": variant_name,
            "in_stock": in_stock,
        })

    return stocks


def _map_variant_name(data_type: str) -> str:
    """
    映射日文规格名称到统一显示名称。
    移植自 content.js 的 mapVariantName()。
    """
    if not data_type:
        return "不明"

    if "ハード" in data_type or data_type == "レビュラーhard":
        return "レビュラーhard"
    if data_type in ("レザラー", "レビュラー", "レギュラー"):
        return "レビュラー"
    if data_type == "ソフト":
        return "ソフト"
    if "ベリー" in data_type:
        return "ベリーソフト"
    if "リッチ" in data_type:
        return "リッチソフト"

    return data_type
