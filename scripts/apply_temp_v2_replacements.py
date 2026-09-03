#!/usr/bin/env python3
"""Apply explicitly reviewed replacements from the temp-v2 collection.

Every entry names both expected file hashes.  A matching filename, catalogue
identity, or page count is deliberately insufficient to overwrite a paper.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import tempfile
from pathlib import Path
from urllib.parse import quote

from stats import CATALOG, ROOT

REPLACEMENTS = {
    "temp-2024-生物-4cc5169272d9": {
        "source": "temp/版本2：生物（按省份分类）2008-2024/2010-2024·（辽宁）生物高考真题/2024年高考生物试卷（辽宁）（空白卷）.pdf",
        "old_sha256": "4cc5169272d91080fdfc66da8561592fbd2a8f1d13020c1ed184aab989cab46f",
        "new_sha256": "82d119e44c930e901c9090b0f7c3b082c33a1ac68b4581e2dacabdbd556f354f",
        "title": "2024年普通高等学校招生选择性考试（辽宁卷）生物学",
        "paper_type": "辽宁卷",
        "region": "LN",
        "local_path": "papers/2024/LN/生物/辽宁生物-试题-p.pdf",
        "note": (
            "内容复核：全文题干相似度 0.901；逐页视觉抽样确认钙调蛋白、森林群落选择题及末页 Bt 基因重组棉花图题一致。"
            "新版本保留“第 1 页/共 11 页”页码及完整正式卷首，旧版为 8 页重排版，故替换为新版本。"
            "文件标题与内容均明确为辽宁卷，修正原先误置于全国目录的记录。"
        ),
    },
    "temp-2024-物理-26a9eb5f2e83": {
        "source": "temp/版本2：物理（按省份分类）2008-2024/2008-2024·（广西）物理高考真题/2024年高考物理试卷（广西）（空白卷）.pdf",
        "old_sha256": "26a9eb5f2e83dbffbbf2cfa14a73125006f0ba3d6ec313f81349ebc16afceb3a",
        "new_sha256": "f05392a8398a47c6c15e80536e3769b4f443686764ac8eb53d1415cab220f773",
        "title": "2024年普通高中学业水平选择性考试（广西卷）物理",
        "paper_type": "广西卷",
        "note": (
            "内容复核：全文题干相似度 0.914；逐页视觉抽样确认潮汐、货箱斜面题及末页齿轮—磁场阻力装置图题一致。"
            "新版本保留“第 1 页/共 7 页”页码及完整正式卷首，旧版为 5 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-地理-4c5c9e4afe88": {
        "source": "temp/版本2：地理（按省份分类）2008-2024/2008-2024·（内蒙古）地理高考真题/2024年高考地理试卷（全国甲卷）（空白卷）.pdf",
        "old_sha256": "4c5c9e4afe88e6b560cd7dd8095b613c81885d1a1b992292370152d5cf48a724",
        "new_sha256": "22e1a7de855c723d86ce498894b843bad7e58c1c1c996a05df6eda67050eba80",
        "title": "2024年普通高等学校招生全国统一考试（全国甲卷）地理",
        "paper_type": "全国甲卷",
        "note": (
            "内容复核：全文题干相似度 0.914；逐页视觉抽样确认苏州工业园图、冰川老鼠照片及末页汉代河湖、旅游地理材料题一致。"
            "新版本保留“第 1 页/共 4 页”页码及完整正式卷首，旧版为 3 页重排版，故替换为新版本。"
            "候选虽位于省份分类目录，但卷首明确为全国甲卷，仍按全国唯一身份归档。"
        ),
    },
    "temp-2024-地理-cadfc7115c4f": {
        "source": "temp/版本2：地理（按省份分类）2008-2024/2010-2024·（辽宁）地理高考真题/2024年高考地理试卷（辽宁）（空白卷）.pdf",
        "old_sha256": "cadfc7115c4f14ec9b4beb644a8eebcbffb210c83f6ddbe199b65df0eb175d25",
        "new_sha256": "489e94aea9a745387c8a5d5972fe4889340c809792d1e34688f2c4adf8c669af",
        "title": "2024年普通高等学校招生选择性考试（辽宁卷）地理",
        "paper_type": "辽宁卷",
        "region": "LN",
        "local_path": "papers/2024/LN/地理/辽宁地理-试题-p.pdf",
        "note": (
            "内容复核：全文题干相似度 0.882；逐页视觉抽样确认泥炭、土壤剖面选择题及末页辽宁地区地质/火山材料地图、平流层影响图表题一致。"
            "新版本保留“机密★启用前”、完整正式卷首和“第 1 页/共 7 页”页码，旧版为 4 页重排版，故替换为新版本。"
            "文件标题与内容均明确为辽宁卷，修正原先误置于全国目录的记录。"
        ),
    },
    "temp-2024-地理-6527f82bee11": {
        "source": "temp/版本2：地理（按省份分类）2008-2024/2012-2024·（安徽）地理高考真题/2024年高考地理试卷（安徽）（空白卷）.pdf",
        "old_sha256": "6527f82bee1186bd781fa1c2dababc9040d688bd546d5c53809a9b8bab7408ce",
        "new_sha256": "48b6bcf5955037984bda3d591cf8b1e42e55444e5793bc0e3e9aa883a72f27c7",
        "title": "安徽省2024年普通高中学业水平选择性考试地理",
        "paper_type": "安徽卷",
        "note": (
            "内容复核：全文题干相似度 0.915；逐页视觉抽样确认河津玻璃产业时间轴、佛手种植剖面照片及末页南美河流材料图题一致。"
            "新版本保留“第 1 页/共 7 页”页码及完整正式标题，旧版为 5 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-地理-cb10bdcd1e47": {
        "source": "temp/版本2：地理（按省份分类）2008-2024/2008-2024·（甘肃）地理高考真题/2024年高考地理试卷（甘肃）（空白卷）.pdf",
        "old_sha256": "cb10bdcd1e478c32ed94f67889d6fc4e77a1bcde9f357cd3c203558f6c3239de",
        "new_sha256": "570a45c0386b4149266ff827377175d33fe90dc810107295b071531e5fcd762b",
        "title": "甘肃省2024年普通高中学业水平等级性考试地理",
        "paper_type": "甘肃卷",
        "note": (
            "内容复核：全文题干相似度 0.905；逐页视觉抽样确认陕电入皖工程、柬华应用科技大学等首页材料及末页凯尔盖朗海台等深线、祁连山草原牧区—农区协同发展图题一致。"
            "新版本保留完整正式卷首和“第 1 页/共 5 页”页码，旧版为 4 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-地理-e28c431238d5": {
        "source": "temp/版本2：地理（按省份分类）2008-2024/2008-2024·（湖北）地理高考真题/2024年高考地理试卷（湖北）（空白卷）.pdf",
        "old_sha256": "e28c431238d5fd90632021d517ddabcfa9fa3255bc0382af2d525ffa68105807",
        "new_sha256": "b7c3de6904f311ec72acb780b0944951e74d4601263f9e38b2863980095235b7",
        "title": "2024年湖北省普通高中学业水平选择性考试地理",
        "paper_type": "湖北卷",
        "note": (
            "内容复核：全文题干相似度 0.887；逐页视觉抽样确认武汉大学樱花花期、食物碳足迹等首页材料及末页育空河冻土层—河流交换示意图题一致。"
            "新版本保留“机密★启用前”、完整正式卷首和“第 1 页/共 7 页”页码，旧版为 5 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-地理-a97feda1207d": {
        "source": "temp/版本2：地理（按省份分类）2008-2024/2012-2024·（福建）地理高考真题/2024年高考地理试卷（福建）（空白卷）.pdf",
        "old_sha256": "a97feda1207d4e2d3ef5d381f40c617e5a71155deacee3e5e626a17b7f6eef86",
        "new_sha256": "f9fc05af68221b8240f3961b3da644826a384893257be5a88f35a58e5dd34ed0",
        "title": "2024年福建省普通高中学业水平选择性考试地理",
        "paper_type": "福建卷",
        "note": (
            "内容复核：全文题干相似度 0.894；逐页视觉抽样确认乡村振兴区位条件、产业协作等首页材料及末页南方某丘陵水土流失生态治理的年产水量、年产沙量表格和剖面图题一致。"
            "新版本保留“绝密★本学科试卷启用前”、完整正式卷首和“第 1 页/共 6 页”页码，旧版为 5 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-物理-340648ba37d0": {
        "source": "temp/版本2：物理（按省份分类）2008-2024/2008-2024·（山东）物理高考真题/2024年高考物理试卷（山东）（空白卷）.pdf",
        "old_sha256": "340648ba37d0ff2aa60c265fab15ee202b42b90aeff14bd200cdd225132713ad",
        "new_sha256": "702d6905bf7e8bddf4e0362b4e8c7dc5062b3f10be1a3fff85a7475c9aff71d6",
        "title": "2024年全省普通高中学业水平等级考试物理",
        "paper_type": "山东卷",
        "note": (
            "内容复核：全文题干相似度 0.918；逐页视觉抽样确认航天核电池、人形机器人、木板题及末页轨道、磁场题图一致。"
            "新版本保留“第 1 页/共 9 页”页码及完整正式标题，旧版为 7 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-物理-d8aab923fc13": {
        "source": "temp/版本2：物理（按省份分类）2008-2024/2012-2024·（安徽）物理高考真题/2024年高考物理试卷（安徽）（空白卷）.pdf",
        "old_sha256": "d8aab923fc13c2bcfc8af04f94cda58c7890e09bacdade567587ede02b87223b",
        "new_sha256": "f5656aa1f6a64ca56c6a223f9da774fedb3f87b326ee651a62d785cbaed307ac",
        "title": "2024年安徽省普通高中学业水平选择性考试物理",
        "paper_type": "安徽卷",
        "note": (
            "内容复核：全文题干相似度 0.908；逐页视觉抽样确认氢原子能级、传送带选择题及末页汽车轮胎、小球与圆弧轨道、电磁感应装置图题一致。"
            "新版本保留完整正式卷首和“第 1 页/共 8 页”页码，旧版为 6 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-生物-008eb3022472": {
        "source": "temp/版本2：生物（按省份分类）2008-2024/2008-2024·（湖北）生物高考真题/2024年高考生物试卷（湖北）（空白卷）.pdf",
        "old_sha256": "008eb3022472bc448336c675355558426ddc46bfc1eb8da33137becf5a56992e",
        "new_sha256": "829dec2575533163691caeef297531145bf02766e868952ba80a6ac87236eedf",
        "title": "2024年湖北省普通高中学业水平选择性考试生物学",
        "paper_type": "湖北卷",
        "note": (
            "内容复核：全文题干相似度 0.919；逐页视觉抽样确认醋酸菌、长江生态选择题及末页 CO₂ 气孔图、遗传系谱和电泳图题一致。"
            "新版本保留“机密★启用前”、完整正式标题和“第 1 页/共 8 页”页码，旧版为 5 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-物理-03cfa42b074e": {
        "source": "temp/版本2：物理（按省份分类）2008-2024/2008-2024·（湖北）物理高考真题/2024年高考物理试卷（湖北）（空白卷）.pdf",
        "old_sha256": "03cfa42b074e604affbf784d83ebb61dae707a1e3725fb9463c7317bbd0d249a",
        "new_sha256": "ceb8bff3049b75cd078b6eb8bc9c9091042c3098a1d06bf2e180478aae6af854",
        "title": "2024年湖北省普通高中学业水平选择性考试物理",
        "paper_type": "湖北卷",
        "note": (
            "内容复核：全文题干相似度 0.903；逐页视觉抽样确认雷击、硼中子俘获、青蛙荷叶等首页选择题及末页传送带—单摆、金属棒与金属环电磁感应图题一致。"
            "新版本保留完整正式卷首和“第 1 页/共 7 页”页码，旧版为 5 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-物理-a5ec05e4c1c9": {
        "source": "temp/版本2：物理（按省份分类）2008-2024/2008-2024·（江西）物理高考真题/2024年高考物理试卷（江西）（空白卷）.pdf",
        "old_sha256": "a5ec05e4c1c9e1f5194c280d35b64e0e919ae71ee4ca43e824796231ff0fc061",
        "new_sha256": "975f5f475e1a540f7d1c3611058dd392573111b0d0b336d410adfa9d1d35216b",
        "title": "2024年普通高等学校招生全国统一考试物理（江西卷）",
        "paper_type": "江西卷",
        "note": (
            "内容复核：全文题干相似度 0.893；逐页视觉抽样确认带电粒子、氮化镓 LED 等首页选择题及末页圆盘转椅、斜面导轨电磁感应图题一致。"
            "新版本保留完整正式卷首和“第 1 页/共 8 页”页码，旧版为 6 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-物理-3007d7d8be7e": {
        "source": "temp/版本2：物理（按省份分类）2008-2024/2008-2024·（河北）物理高考真题/2024年高考物理试卷（河北）（空白卷）.pdf",
        "old_sha256": "3007d7d8be7e77a3df2c930944f42626b4b3f2eb235f3f4d2e70fb7b62b1d10e",
        "new_sha256": "7b5e8f27c98ca59dcd738a2b83ef369391a4147f0114e122766c92afb8bba6fc",
        "title": "2024年普通高中学业水平选择性考试（河北卷）物理试题",
        "paper_type": "河北卷",
        "note": (
            "内容复核：全文题干相似度 0.920；逐页视觉抽样确认首页电场、篮球图题及末页机器人木板题图一致。"
            "新版本保留“第 1 页/共 8 页”页码及完整正式卷首，旧版为 7 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-生物-b7d43219ecc9": {
        "source": "temp/版本2：生物（按省份分类）2008-2024/2008-2024·（甘肃）生物高考真题/2024年高考生物试卷（甘肃）（空白卷）.pdf",
        "old_sha256": "b7d43219ecc90785324f55af6e7e5ba9af32d789c322e9c3b36a1572825712c0",
        "new_sha256": "6346cdb6445ca6c4d69d3635e0a3e3e77d4426703e37d589662f31044ef6514b",
        "title": "2024年甘肃省普通高校招生统一考试生物学",
        "paper_type": "甘肃卷",
        "note": (
            "内容复核：全文题干相似度 0.922；逐页视觉抽样确认“武都油橄榄”选择题及末页纤维素酶质粒构建、协同系数表格题一致。"
            "新版本保留“第 1 页/共 10 页”页码及完整正式标题，旧版为 6 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-生物-c28694e65308": {
        "source": "temp/版本2：生物（按省份分类）2008-2024/2008-2024·（河北）生物高考真题/2024年高考生物试卷（河北）（空白卷）.pdf",
        "old_sha256": "c28694e65308e562a0843e0700b9c7fcf5a269b8ec13e2b8b0afda5eaf2c0509",
        "new_sha256": "077c81ab9ee697d096da69d0afc39658f2dff5e7ac0086d5c732a330884f5960",
        "title": "2024年普通高中学业水平选择性考试（河北卷）生物学",
        "paper_type": "河北卷",
        "note": (
            "内容复核：全文题干相似度 0.896；逐页视觉抽样确认细胞、酶、DNA 损伤等首页选择题及末页西瓜性状遗传、SSR 电泳图题一致。"
            "新版本保留完整正式卷首和“第 1 页/共 9 页”页码，旧版为 6 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-生物-80efc04d9ec6": {
        "source": "temp/版本2：生物（按省份分类）2008-2024/2008-2024·（广东）生物高考真题/2024年高考生物试卷（广东）（空白卷）.pdf",
        "old_sha256": "80efc04d9ec65cc287524eb1a94d65f78e89ad60e92ba3441f2e7baa497080b3",
        "new_sha256": "d3bde4db925411b608fffce54d27fbdbc670b24d643fbf3ba98f1727b946dda0",
        "title": "2024年广东省普通高中学业水平选择性考试生物",
        "paper_type": "广东卷",
        "note": (
            "内容复核：全文题干相似度 0.923；逐页视觉抽样确认“碳汇渔业”选择题及末页蓝光敏蛋白图、材料题一致。"
            "新版本保留“第 1 页/共 11 页”页码及完整正式标题，旧版为 7 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-历史-abec439eb632": {
        "source": "temp/版本2：历史（按省份分类）2008-2024/2008-2024·（湖北）历史高考真题/2024年高考历史试卷（湖北）（空白卷）.pdf",
        "old_sha256": "abec439eb632166ef421d9a0ee27a2c191b91b4da99d29ba1b35decfa81f35c9",
        "new_sha256": "0699d5bee13cbd63b17cf9be9a01dbfd875b32d0bd58d970de0d708eff8fb5ca",
        "title": "湖北省2024年普通高中学业水平等级考试历史",
        "paper_type": "湖北卷",
        "note": (
            "内容复核：全文题干相似度 0.930；逐页视觉抽样确认“蛋壳陶杯”选择题及末页“物质与文明”表格材料题一致。"
            "新版本保留“第 1 页/共 6 页”页码及完整正式标题，旧版为 4 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-政治-d225361190fe": {
        "source": "temp/版本2：政治（按省份分类）2008-2024/2010-2024·（辽宁）政治高考真题/2024年高考政治试卷（辽宁）（空白卷）.pdf",
        "old_sha256": "d225361190fe41a5734f8c767ec13cd1fb445913490d729c8de85081e04f4847",
        "new_sha256": "135163656649ab04db7682a6181aea87260813a42564d09c3782be1b9c34d2c8",
        "title": "2024年普通高等学校招生选择性考试（辽宁卷）思想政治",
        "paper_type": "辽宁卷",
        "region": "LN",
        "local_path": "papers/2024/LN/政治/辽宁政治-试题-p.pdf",
        "note": (
            "内容复核：全文题干相似度 0.939；逐页视觉抽样确认选择题、末页“冰上丝绸之路”地图和材料题一致。"
            "新版本保留“共 8 页”页码及完整正式标题，旧版为 5 页重排版，故替换为新版本。"
            "文件标题与内容均明确为辽宁卷，修正原先误置于全国目录的记录。"
        ),
    },
    "temp-2024-历史-1c421feb1b55": {
        "source": "temp/版本2：历史（按省份分类）2008-2024/2008-2024·（内蒙古）历史高考真题/2024年高考历史试卷（全国甲卷）（空白卷）.pdf",
        "old_sha256": "1c421feb1b55f909c241e20508e701732a5ef0fd81d0678bf90ac04122493836",
        "new_sha256": "67c664e93239da6ee17e5d4a11b96eab6d447c874911864166fa05c30df761a6",
        "title": "2024年普通高等学校招生全国统一考试（全国甲卷）历史",
        "paper_type": "全国甲卷",
        "note": (
            "内容复核：全文题干相似度 0.933；逐页视觉抽样确认选择题、县域阶层表格和末页材料分析题一致。"
            "新版本保留密级、正式卷首及“共 5 页”页码，旧版为 3 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-地理-7754a9ff6d1b": {
        "source": "temp/版本2：地理（按省份分类）2008-2024/2008-2024·（山东）地理高考真题/2024年高考地理试卷（山东）（空白卷）.pdf",
        "old_sha256": "7754a9ff6d1b64752de97879a924f2aa3877e3071a3542952b0748e44bf419ad",
        "new_sha256": "b608a3cc6fddf4309bed4f219355a09891bd5b661aea1a0e48c91b6f8f5a8a5a",
        "title": "山东省2024年普通高中学业水平等级考试地理",
        "paper_type": "山东卷",
        "note": (
            "内容复核：全文题干相似度 0.935；逐页视觉抽样确认平贝材料、岛屿图及末页丹江口水库调度图题一致。"
            "新版本保留“共 7 页”页码及完整正式标题，旧版为 5 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-地理-83ae121d6eb8": {
        "source": "temp/版本2：地理（按省份分类）2008-2024/2008-2024·（湖南）地理高考真题/2024年高考地理试卷（湖南）（空白卷）.pdf",
        "old_sha256": "83ae121d6eb8413602f5f35c81f77cc410bff18c61ca7540b8bd303b495e62dd",
        "new_sha256": "569c0dc4d5ee383ea64b60ecdbb5a83e3b2c688f2d32cba3ccb464c6af93b69d",
        "title": "湖南省2024年普通高中学业水平选择性考试地理",
        "paper_type": "湖南卷",
        "note": (
            "内容复核：全文题干相似度 0.918；逐页视觉抽样确认石牌豆腐材料、人口年龄结构图及末页中华鬣羚分布图题一致。"
            "新版本保留“共 7 页”页码及完整正式标题，旧版为 5 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-生物-c257340160f9": {
        "source": "temp/版本2：生物（按省份分类）2008-2024/2008-2024·（山东）生物高考真题/2024年高考生物试卷（山东）（空白卷）.pdf",
        "old_sha256": "c257340160f9af783a47af9219e1401eab7c9146f099658e594e410f9012de9e",
        "new_sha256": "eb49e524d63da38708f566b3de35375a055df7afb090b31b37b5d4b49fd0d6e2",
        "title": "2024年全省普通高中学业水平等级考试生物",
        "paper_type": "山东卷",
        "note": (
            "内容复核：全文题干相似度 0.925；逐页视觉抽样确认第 1–6 题及末页转基因大豆实验题图和题干一致。"
            "新版本保留“共 11 页”页码和密级页眉，旧版为 7 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-历史-169a991ffaf3": {
        "source": "temp/版本2：历史（按省份分类）2008-2024/2008-2024·（山东）历史高考真题/2024年高考历史试卷（山东）（空白卷）.pdf",
        "old_sha256": "169a991ffaf371854ec96ecb88922b5cc9346c59fb9ce7c1d323ab278a0db272",
        "new_sha256": "775e3e3c5f4a5d807728f72f0b2490c3599a2383252021055c9b47336cd4f8c1",
        "title": "山东省2024年普通高中学业水平等级考试历史",
        "paper_type": "山东卷",
        "note": (
            "内容复核：全文题干相似度 0.948；逐页视觉抽样确认第 1–5 题、表格材料及末页非洲史材料题一致。"
            "新版本保留“共 8 页”页码及完整正式标题，旧版为 5 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-物理-4b8b23f5acb1": {
        "source": "temp/版本2：物理（按省份分类）2008-2024/2008-2024·（湖南）物理高考真题/2024年高考物理试卷（湖南）（空白卷）.pdf",
        "old_sha256": "4b8b23f5acb1e82820b34de666372c9293d16b68526fb6d3d515ce1f3133fb45",
        "new_sha256": "53a18dc3499d46b71a283244b5375344a69ef6b82c60327a88571acb101914e7",
        "title": "2024年普通高中学业水平选择性考试（湖南卷）物理",
        "paper_type": "湖南卷",
        "note": (
            "内容复核：全文题干相似度 0.929；逐页视觉抽样确认第 1–6 题和末页圆轨道题图一致。"
            "新版本保留“共 8 页”页码及正式卷首，旧版为 6 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-政治-8360f67645d2": {
        "source": "temp/版本2：政治（按省份分类）2008-2024/2008-2024·（山东）政治高考真题/2024年高考政治试卷（山东）（空白卷）.pdf",
        "old_sha256": "8360f67645d2b3c13eb4ae2acec799a9bf1ab43db678fbe3f33bc8efbeeb1c4b",
        "new_sha256": "670459b88c6624489c0cb13ff1cf4e7631ac38fcd3b2a5496cef1d4741e3c4e1",
        "title": "2024年全省普通高中学业水平等级考试思想政治",
        "paper_type": "山东卷",
        "note": (
            "内容复核：全文题干相似度 0.953；逐页视觉抽样确认选择题、图表材料及第 18–19 题一致。"
            "新版本保留“共 8 页”页码及完整正式页眉，旧版为 5 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-政治-1e6d66279d3e": {
        "source": "temp/版本2：政治（按省份分类）2008-2024/2008-2024·（湖南）政治高考真题/2024年高考政治试卷（湖南）（空白卷）.pdf",
        "old_sha256": "1e6d66279d3ebb5075df46b4b565c5ec0d49d5f468d5ddd01b92a5b8991c447e",
        "new_sha256": "3b5e2b1bbdab2f3c82b4948db068fc94e93458f0775d5bb993a96c0b8f2fda4f",
        "title": "2024年湖南省普通高中学业水平选择性考试思想政治",
        "paper_type": "湖南卷",
        "note": (
            "内容复核：全文题干相似度 0.960；逐页视觉抽样确认选择题、第 20 题和思维导图一致。"
            "新版本保留“共 8 页”页码及完整正式页眉，旧版为 5 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-数学-3056423645c4": {
        "source": "temp/版本2：数学（按省份分类）2008-2024/2008-2024·（山东）数学高考真题/2024年高考数学试卷（新课标Ⅰ卷）（空白卷）.pdf",
        "old_sha256": "3056423645c4bc35e8bf2ad96f431bed0f140865a5de1a96d75fcd760c549e7e",
        "new_sha256": "e241a28d4a53514825796a4d137a93dc5b56794b91c940ebd8e72bf8429ce2ce",
        "title": "2024年普通高等学校招生全国统一考试数学（新课标Ⅰ卷）",
        "paper_type": "新课标Ⅰ卷",
        "note": (
            "内容复核：与旧版视觉抽样比较，首页选择题及末页第 17–19 题一致；"
            "新版本保留正式页眉和“共 4 页”页码，旧版为无页眉的 3 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-英语-e5777ae7fee5": {
        "source": "temp/版本2：英语（按省份分类）2008-2024/2008-2024·（山东）英语高考真题/2024年高考英语试卷（新课标Ⅰ卷）（空白卷）.pdf",
        "old_sha256": "e5777ae7fee55ff33a4d8c9171a15f0eeeeed56759625f26470e8f439d62178f",
        "new_sha256": "41a0e1c61d5ae1ab404d96a057fb815c2103c321a740829fa2e2d8a976ca6382",
        "title": "2024年普通高等学校招生全国统一考试（新课标Ⅰ卷）英语",
        "paper_type": "新课标Ⅰ卷",
        "note": (
            "内容复核：全文题干相似度 0.877；逐页视觉抽样确认听力选择题及末页 Prague 乘车经历续写题的题干、提示语和答题区域一致。"
            "新版本保留完整正式卷首和“第 1 页/共 12 页”页码，旧版为 7 页重排版，故替换为新版本。"
            "候选虽位于省份分类目录，但卷首明确为新课标Ⅰ卷，仍按全国唯一身份归档。"
        ),
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def planned_replacements(
    rows: list[dict[str, str]],
) -> list[tuple[dict[str, str], dict[str, str], Path, Path, Path]]:
    by_id = {row["record_id"]: row for row in rows}
    plans = []
    for record_id, decision in REPLACEMENTS.items():
        row = by_id.get(record_id)
        if row is None:
            raise ValueError(f"replacement record not found: {record_id}")
        source = ROOT / decision["source"]
        current_destination = ROOT / row["local_path"]
        destination = ROOT / decision.get("local_path", row["local_path"])
        if not source.is_file() or not current_destination.is_file():
            raise FileNotFoundError(f"replacement files missing for {record_id}")
        current_hash = sha256(current_destination)
        if row.get("sha256") == decision["new_sha256"] and current_hash == decision["new_sha256"]:
            continue
        if row.get("sha256") != decision["old_sha256"] or current_hash != decision["old_sha256"]:
            raise ValueError(f"unexpected current hash for {record_id}")
        if sha256(source) != decision["new_sha256"]:
            raise ValueError(f"unexpected candidate hash for {record_id}")
        if destination != current_destination and destination.exists():
            raise FileExistsError(f"new destination already exists for {record_id}: {destination}")
        plans.append((row, decision, source, current_destination, destination))
    return plans


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="replace reviewed files and update the catalog")
    args = parser.parse_args()
    with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    plans = planned_replacements(rows)
    for row, _, source, _, destination in plans:
        print(f"{row['record_id']}: {source.relative_to(ROOT)} -> {destination.relative_to(ROOT)}")
    print(f"replacements={len(plans)} mode={'apply' if args.apply else 'dry-run'}")
    if not args.apply:
        return 0
    for row, decision, source, current_destination, destination in plans:
        destination.parent.mkdir(parents=True, exist_ok=True)
        staged = destination.with_name(f".{destination.name}.temp-v2")
        shutil.copy2(source, staged)
        staged.replace(destination)
        if current_destination != destination:
            current_destination.unlink()
        row["sha256"] = decision["new_sha256"]
        row["title"] = decision["title"]
        row["paper_type"] = decision["paper_type"]
        row["region"] = decision.get("region", row["region"])
        row["local_path"] = decision.get("local_path", row["local_path"])
        row["source_url"] = f"local://{quote(decision['source'], safe='/')}"
        if decision["note"] not in row["notes"]:
            row["notes"] = f"{row['notes']}；{decision['note']}"
    with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", dir=CATALOG.parent, delete=False) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        temporary = Path(handle.name)
    temporary.replace(CATALOG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
