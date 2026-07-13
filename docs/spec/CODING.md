# 编码规范 (CODING.md)

FRP 后端与前端编写必须遵守以下编码守则：

## 后端规范
* 必须遵循 **PEP 8** 风格指南。
* 所有的 API 路由器、CRUD、Service 方法必须包含完整的 Python Type Hints 类型标注。
* 类名使用驼峰命名法（`CamelCase`），变量及函数名使用下划线法（`snake_case`）。
* 注释默认使用中文，解释“为什么”这么设计，而非“怎么做”。

## 前端规范
* 组件统一采用 Vue 3 `<script setup lang="ts">` 组合式 API 写法。
* 变量、函数命名采用驼峰命名法（`camelCase`）。
* 使用 TailwindCSS 排版，样式避免使用 inline 魔法数。