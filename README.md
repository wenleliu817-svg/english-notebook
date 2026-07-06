# English Notebook

本地英语课程记录 & 单词本工具。

## 功能

- **链接解析**：粘贴 URL，自动提取标题、摘要、正文，一键创建课程记录
- **课程管理**：记录每节课的主题、笔记、作业、来源链接
- **单词本**：音标、释义、例句、难度星级、标签、关联课程
- **复习模式**：随机抽词，闪卡式复习，自动调整难度
- **全局搜索**：跨课程和单词搜索，关键词高亮
- **GitHub 同步**：通过 SSH/git 一键同步数据
- **数据导入导出**：JSON 格式备份

## 使用

```bash
cd english-notebook
python3 server.py
```

浏览器打开 http://localhost:7799

## GitHub 同步设置

1. 将本目录初始化为 git 仓库并关联远程：

```bash
cd english-notebook
git remote add origin git@github.com:wenleliu817/english-notebook.git
```

2. 在页面右上角点击 ⬆ 按钮即可同步

## 数据存储

- 本地：`data.json`
- 远程：GitHub 仓库
- 备用：浏览器 localStorage
