# 大魔王库存监控插件

Chrome浏览器插件，用于监控 daimaoh.co.jp 网站商品库存。

## 功能

- 监控商品5种规格的库存状态
- 实时显示 在庫あり/在庫なし
- 历史记录保存
- 纯前端运行，无需后端

## 安装步骤

### 1. 生成图标

在终端运行以下命令生成图标：

```bash
cd stock-monitor
node -e "
const fs = require('fs');
const zlib = require('zlib');
function crc32(d){let c=0xffffffff;const t=[];for(let n=0;n<256;n++){let x=n;for(let k=0;k<8;k++)x=x&1?0xedb88320^(x>>>1):x>>>1;t[n]=x}for(let i=0;i<d.length;i++)c=t[(c^d[i])&255]^(c>>>8);return c^0xffffffff}
function chunk(t,d){const l=Buffer.alloc(4);l.writeUInt32BE(d.length,0);const b=Buffer.concat([Buffer.from(t),d]);const c=Buffer.alloc(4);c.writeUInt32BE(crc32(b)>>>0,0);return Buffer.concat([l,b,c])}
function png(s){const w=s,h=s,d=Buffer.alloc((w*4+1)*h);for(let y=0;y<h;y++){d[y*(w*4+1)]=0;for(let x=0;x<w;x++){const o=y*(w*4+1)+1+x*4;d[o]=233;d[o+1]=69;d[o+2]=96;d[o+3]=255}}return Buffer.concat([Buffer.from([0x89,80,78,71,13,10,26,10]),chunk('IHDR',Buffer.from([w>>24,w>>16&255,w>>8&255,w&255,h>>24,h>>16&255,h>>8&255,h&255,8,6,0,0,0])),chunk('IDAT',zlib.deflateSync(d)),chunk('IEND',Buffer.alloc(0))])}
[16,48,128].forEach(s=>fs.writeFileSync('icons/icon'+s+'.png',png(s)))
"
```

### 2. 安装插件

1. 打开Chrome，访问 `chrome://extensions/`
2. 开启右上角的「开发者模式」
3. 点击「加载已解压的扩展程序」
4. 选择 `stock-monitor` 文件夹

### 3. 使用

1. 打开大魔王网站商品页面（如 item5457.html）
2. 点击地址栏右侧的插件图标
3. 即可看到5种规格的库存状态

## 规格说明

| 规格名 | 日语 |
|--------|------|
| レギュラーハード | 最硬 |
| レギュラー | 标准 |
| ソフト | 柔软 |
| ベリーソフト | 超柔软 |
| リッチソフト | 最软 |

## 输出格式

- ✅ 在庫あり = 有库存
- ❌ 在庫なし = 无库存

## 文件结构

```
stock-monitor/
├── manifest.json      # 插件配置
├── popup.html         # 弹窗界面
├── popup.css          # 弹窗样式
├── popup.js           # 弹窗逻辑
├── content.js         # 页面内容脚本
└── icons/
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```
