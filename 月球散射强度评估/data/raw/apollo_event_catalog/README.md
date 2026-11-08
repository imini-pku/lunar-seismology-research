# Apollo 事件目录

本目录保存本轮覆盖审计下载的公开目录文件，来源为 NASA/PDS Apollo Expanded Event Catalog：

- `levent.1008weber.csv`：综合事件/台站 trace 标志表，共 13,057 行；
- `nakamura_2005_dm_locations.csv`：深月震源区；
- `nakamura_1979_sm_locations.csv`：浅月震位置；
- `nakamura_1983_ai_locations.csv`：人工撞击位置；
- `gagnepian_2006_catalog.csv`：人工撞击和部分自然撞击位置；
- `lognonne_2003_catalog.csv`、各类 arrivals 文件：保留用于后续时间匹配和到时核查。

正式反演仍需从 Apollo PSE 数据包下载 MiniSEED/GeoCSV 波形并按 StationXML 进行响应校正。
