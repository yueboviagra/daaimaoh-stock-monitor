// Popup Script - 通过后台tab注入脚本获取库存

const STORAGE_KEY = 'stock_history';

// 监控的商品列表
const PRODUCTS = [
  { url: 'https://daimaoh.co.jp/item5457.html', name: 'Muses Fillo（ミューゼス・フィロ）' },
  { url: 'https://daimaoh.co.jp/item1663.html', name: 'Venus Real（ヴィーナス・リアル）' },
  { url: 'https://daimaoh.co.jp/item1608.html', name: 'Venus Clone（ヴィーナス・クローン）' },
  { url: 'https://daimaoh.co.jp/item1662.html', name: 'Venus Cross（ヴィーナス・クロス）' }
];

// DOM元素
const loading = document.getElementById('loading');
const loadingText = document.getElementById('loading').querySelector('p');
const errorDiv = document.getElementById('error');
const errorMessage = document.getElementById('error-message');
const resultsDiv = document.getElementById('results');
const productList = document.getElementById('product-list');
const refreshBtn = document.getElementById('refresh-btn');
const toggleHistoryBtn = document.getElementById('toggle-history');
const historyDiv = document.getElementById('history');
const historyList = document.getElementById('history-list');
const clearHistoryBtn = document.getElementById('clear-history');
const urlInput = document.getElementById('url-input');
const checkUrlBtn = document.getElementById('check-url-btn');
const presetBtns = document.querySelectorAll('.preset-btn');

document.addEventListener('DOMContentLoaded', init);

async function init() {
  refreshBtn.addEventListener('click', () => checkProducts(PRODUCTS));
  toggleHistoryBtn.addEventListener('click', toggleHistory);
  clearHistoryBtn.addEventListener('click', clearHistory);
  checkUrlBtn.addEventListener('click', () => {
    const url = urlInput.value.trim();
    if (!url) return;
    if (!url.includes('daimaoh.co.jp')) {
      showError('请输入大魔王网站的URL');
      return;
    }
    checkProducts([{ url, name: extractNameFromUrl(url) }]);
  });
  urlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') checkUrlBtn.click();
  });
  presetBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      urlInput.value = btn.dataset.url;
      checkUrlBtn.click();
    });
  });
  await loadHistory();
  // 打开插件时自动检查所有商品库存
  checkProducts(PRODUCTS);
}

function extractNameFromUrl(url) {
  const match = url.match(/item(\d+)/);
  return match ? `商品${match[1]}` : '未知商品';
}

// ====== 核心：通过后台tab注入脚本检查库存 ======

async function checkProducts(products) {
  showLoading(true, `正在检查 ${products.length} 个商品...`);
  hideError();
  resultsDiv.style.display = 'none';

  const results = [];

  for (let i = 0; i < products.length; i++) {
    const product = products[i];
    showLoading(true, `正在检查 ${product.name} (${i + 1}/${products.length})...`);

    try {
      const stockData = await checkSingleProduct(product.url);
      results.push({
        url: product.url,
        name: stockData.productName || product.name,
        stocks: stockData.stocks || [],
        error: stockData.error
      });
    } catch (err) {
      results.push({
        url: product.url,
        name: product.name,
        stocks: [],
        error: err.message
      });
    }
  }

  displayResults(results);
  showLoading(false);

  if (results.some(r => r.stocks.length > 0)) {
    await saveHistory(results);
  }
}

async function checkSingleProduct(url) {
  // 1. 创建后台tab
  const tab = await chrome.tabs.create({ url, active: false });

  try {
    // 2. 等待tab加载完成
    await waitForTabLoad(tab.id);

    // 3. 注入脚本获取库存
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ['js/content.js']
    });

    return result.result || { error: '脚本未返回结果' };
  } finally {
    // 4. 关闭tab
    try { await chrome.tabs.remove(tab.id); } catch (e) { /* ignore */ }
  }
}

function waitForTabLoad(tabId) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      reject(new Error('页面加载超时'));
    }, 30000);

    function listener(updatedTabId, changeInfo) {
      if (updatedTabId === tabId && changeInfo.status === 'complete') {
        clearTimeout(timeout);
        chrome.tabs.onUpdated.removeListener(listener);
        // 额外等待让年龄验证弹窗和JavaScript执行完
        setTimeout(resolve, 2000);
      }
    }

    chrome.tabs.onUpdated.addListener(listener);
  });
}

// ====== UI函数 ======

function displayResults(results) {
  resultsDiv.style.display = 'block';
  productList.innerHTML = '';

  for (const product of results) {
    const div = document.createElement('div');
    div.className = 'product-card';

    if (product.error && product.stocks.length === 0) {
      div.innerHTML = `
        <div class="product-header">
          <h3>${escapeHtml(product.name)}</h3>
          <span class="error-tag">获取失败</span>
        </div>
        <a href="${product.url}" target="_blank" class="product-url">${product.url}</a>
        <p class="error-detail">${escapeHtml(product.error)}</p>
      `;
    } else {
      const inStockCount = product.stocks.filter(s => s.inStock).length;
      const totalCount = product.stocks.length;

      const stockItems = product.stocks.map(s => `
        <tr>
          <td class="variant-name">${escapeHtml(s.variant)}</td>
          <td>
            <span class="stock-status ${s.inStock ? 'in-stock' : 'out-of-stock'}">
              ${s.inStock ? '✅ 在庫あり' : '❌ 在庫なし'}
            </span>
          </td>
        </tr>
      `).join('');

      div.innerHTML = `
        <div class="product-header">
          <h3>${escapeHtml(product.name)}</h3>
          ${totalCount > 0 ? `<span class="summary-tag ${inStockCount > 0 ? 'has-stock' : 'no-stock'}">${inStockCount}/${totalCount}</span>` : ''}
        </div>
        <a href="${product.url}" target="_blank" class="product-url">${product.url}</a>
        ${totalCount > 0 ? `
          <table class="stock-table"><tbody>${stockItems}</tbody></table>
        ` : '<p class="no-data">未能获取库存数据</p>'}
      `;
    }

    productList.appendChild(div);
  }
}

function escapeHtml(text) {
  const el = document.createElement('span');
  el.textContent = text || '';
  return el.innerHTML;
}

function showLoading(show, text) {
  loading.style.display = show ? 'block' : 'none';
  if (text) loadingText.textContent = text;
}

function showError(msg) {
  errorDiv.style.display = 'block';
  errorMessage.textContent = msg;
}

function hideError() {
  errorDiv.style.display = 'none';
}

// ====== 历史记录 ======

function toggleHistory() {
  const isHidden = historyDiv.style.display === 'none';
  historyDiv.style.display = isHidden ? 'block' : 'none';
  toggleHistoryBtn.textContent = isHidden ? '📋 收起' : '📋 历史';
}

async function saveHistory(results) {
  try {
    const history = await getHistory();
    const entry = {
      id: Date.now(),
      time: new Date().toLocaleString('ja-JP'),
      products: results.map(p => ({
        name: p.name,
        url: p.url,
        stocks: p.stocks || []
      }))
    };
    history.unshift(entry);
    if (history.length > 50) history.pop();
    await chrome.storage.local.set({ [STORAGE_KEY]: history });
    await loadHistory();
  } catch (e) {
    console.error('保存历史失败:', e);
  }
}

function getHistory() {
  return new Promise((resolve) => {
    chrome.storage.local.get(STORAGE_KEY, data => {
      resolve(data[STORAGE_KEY] || []);
    });
  });
}

async function loadHistory() {
  const history = await getHistory();
  historyList.innerHTML = '';

  if (history.length === 0) {
    historyList.innerHTML = '<p class="no-data">暂无历史记录</p>';
    return;
  }

  for (const entry of history.slice(0, 10)) {
    const div = document.createElement('div');
    div.className = 'history-item';

    const productSummary = entry.products.map(p => {
      const inStock = (p.stocks || []).filter(s => s.inStock).length;
      const total = (p.stocks || []).length;
      return `${p.name}: ${inStock}/${total}`;
    }).join(' | ');

    div.innerHTML = `
      <div class="history-time">${entry.time}</div>
      <div class="history-content">${productSummary}</div>
    `;
    historyList.appendChild(div);
  }
}

async function clearHistory() {
  await chrome.storage.local.set({ [STORAGE_KEY]: [] });
  await loadHistory();
}
