# 審查摘要

1. 先處理 c02 寫死的 POS token：已進版控即視為外洩，需撤換並改用 secret scope。
2. 再處理 c09 MERGE 前未去重：重複 order_id 會讓 MERGE 失敗或寫入錯誤資料。
3. c03 的 .cast 在 ANSI mode 下遇到髒資料會讓整批失敗，改 try_cast。
其餘：c07 仍讀 hive_metastore、c12 寫死 catalog 且無上限 collect、c10 gold 表前綴錯誤、
c08 轉換函式內寫表、c04 迴圈 withColumn、第 5 個 cell 缺標籤。
