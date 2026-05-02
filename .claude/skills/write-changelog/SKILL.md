---
description: 比对当前分支与 main，写入用户友好的中英文 changelog，提交并打开 PR 页面
disable-model-invocation: true
---

前提1：仅在用户在非 main 分支下、且当前分支已完全提交时，才执行这个 skill。
前提2：如果 OpenLucky.iss 中的版本号与 app/package.json 的版本号不一致，请弹出警告告知用户并退出此 skill。

动作1：更新 main 分支、推送当前分支到远程。
动作2：写入 changelog 文档。分两种情况，一种是带后缀版本，一种是不带后缀的正式版本。
    a. 版本号带后缀，-alphaN -betaN -rcN，带一个后缀和数字的，比如 v1.2.3-rc4，那么执行下面的操作：
       对照当前分支和 main 分支，撰写 changelog（放在 changelog 目录）。
    b. 版本号不带后缀，比如 v1.2.3，那么执行下面的操作：
       阅读此版本的所有后缀分支的 changelog，综合出一个大的变更信息，请注意如果多个后缀版本反复出现对同一内容的多次修改，或者对同一内容的变更和撤回，请合并这些信息为一条。
       将内容撰写到 changelog（放在 changelog 目录）。
动作2文件生成规则：
    英文版文件名：CHANGELOG.en_US.<tag_version>.md
    中文版文件名：CHANGELOG.zh_Hans.<tag_version>.md
    <tag_version> 从 app/package.json 中读取 .version 字段，如果 .version 字段值不带前缀 v，则加上前缀 v 当作 <tag_version>。
    如你提取到 v1.2.3-rc.4.md，那么请生成 `CHANGELOG.en_US.v1.2.3-rc.4.md` 和 `CHANGELOG.zh_Hans.v1.2.3-rc.4.md`。

动作3：增加新的 CHANGELOG 过后，提交当前分支，并推送远程，推送完毕后用浏览器打开当前分支到 main 分支的 Pull Request 页面。

注意，如果有同名文件，则让用户确认是否要替换，如果用户不替换，则不要执行。
注意，描述尽可能简洁，概括一下我改了哪些功能，不要暴露技术细节，下载软件的用户不关心，可能会看得晕头转向。
注意，版本号带的后缀，有点号和没有点号的都是合法的、符合我的预期的，比如 v1.2.3-rc4 或者 比如 v1.2.3-rc.4，请不要自作主张帮我纠正。
