// Content Script - 注入到商品页面，自动检查所有规格库存
// 通过 chrome.scripting.executeScript 注入，不使用消息通信

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function checkAllStock() {
  // 第一步：关闭18岁年龄验证弹窗
  dismissAgeVerification();

  // 等待弹窗关闭
  await sleep(1000);

  // 第二步：获取商品名称
  const productName = getProductName();

  // 第三步：查找变体列表并读取每个规格的库存状态
  const stocks = getVariantsFromList();

  if (stocks.length === 0) {
    return { productName, stocks: [], error: '未找到规格列表' };
  }

  return { productName, stocks, error: null };
}

// 从 <li class="variation_list"> 元素获取变体和库存
function getVariantsFromList() {
  const stocks = [];

  // 查找 variation_list 容器
  const variationList = document.querySelector('.variation_list');
  if (!variationList) return stocks;

  const items = variationList.querySelectorAll('li');

  for (const item of items) {
    // 获取 data-type 属性（规格名称）
    const variantType = item.getAttribute('data-type');
    const displayName = mapVariantName(variantType);

    // 检查库存状态：class 包含 "zero" 表示缺货
    const className = item.className || '';
    const inStock = !className.includes('zero');

    stocks.push({
      variant: displayName,
      inStock: inStock,
      statusText: inStock ? '在庫あり' : '在庫なし'
    });
  }

  return stocks;
}

// 映射日文规格名称到简化的显示名称
function mapVariantName(type) {
  if (!type) return '不明';

  // レギュラーハード / レギュラーソフト等变体名称映射
  if (type.includes('ハード') || type === 'レビュラーhard') {
    return 'レビュラーhard';
  }
  if (type === 'レザラー' || type === 'レビュラー') {
    return 'レビュラー';
  }
  if (type === 'ソフト') return 'ソフト';
  if (type.includes('ベリー')) return 'ベリーソフト';
  if (type.includes('リッチ')) return 'リッチソフト';

  return type;
}

// 关闭年龄验证弹窗
function dismissAgeVerification() {
  // 查找并点击 ENTER 按钮
  const enterBtns = document.querySelectorAll('a, button, input');
  for (const btn of enterBtns) {
    const text = (btn.textContent || btn.value || '').trim();
    if (text === 'ENTER' || text.includes('入口') || text.includes('18歳以上')) {
      btn.click();
      break;
    }
  }

  // 也尝试关闭modal
  const closeBtns = document.querySelectorAll('.modal-close, .close, [class*="close"]');
  for (const btn of closeBtns) {
    if (btn.textContent.includes('×') || btn.textContent.includes('閉じる')) {
      btn.click();
    }
  }

  // 尝试通过简单的modal容器隐藏
  const splashEl = document.querySelector('#splash, .splash, #age-verification, .age-verification, #simplemodal-data');
  if (splashEl) {
    // 直接点击ENTER链接
    const enterLink = splashEl.querySelector('a[href*="enter"], a:has(+ a), li:first-child a');
    if (enterLink) enterLink.click();
  }
}

// 获取商品名称
function getProductName() {
  const h1 = document.querySelector('h1');
  if (h1) {
    const text = h1.textContent.trim();
    if (text.length > 0 && text.length < 200) return text;
  }
  const title = document.querySelector('title');
  if (title) {
    return title.textContent.split(' - ')[0].trim();
  }
  return '未知商品';
}

// 执行检查并返回结果
(async () => {
  const result = await checkAllStock();
  return result;
})();
