from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from food_safety.models import (
    ChecklistItem,
    ChecklistSection,
    ChecklistVersion,
    Sector,
    SectorActivity,
)

SECTORS_CATALOG = [
    {
        "code": "SLA",
        "name_ar": "المسالخ ونحر المواشي والدواجن",
        "name_en": "Slaughterhouses & Livestock/Poultry Processing",
        "activities": [
            ("LIVESTOCK_SLA", "نحر وتجهيز المواشي", "Livestock Slaughtering & Dressing"),
            ("POULTRY_SLA", "ذبح وتجهيز الدواجن", "Poultry Slaughtering & Processing"),
            ("VET_INSPECTION", "الفحص البيطري والختم الصحي", "Ante/Post-Mortem Vet & Stamping"),
        ],
        "extra_sections": [
            (
                "SEC-03",
                "المواصفات البيطرية والذبح الصحي ومعالجة المخلفات",
                "Veterinary Control, Hygienic Slaughtering & By-Products",
                3,
                [
                    ("05", "فحص الحيوانات قبل وبعد الذبح ووجود طبيب بيطري مشرف", "Ante-mortem and post-mortem veterinary inspection", "CRITICAL", Decimal("20.00"), "DOCUMENT"),
                    ("06", "فصل مسارات الحيوانات الحية عن الذبائح ومنع التلوث المتبادل", "Separation of live animals and dressed carcasses", "CRITICAL", Decimal("20.00"), "VISUAL"),
                    ("07", "تنظيف وتعقيم أدوات الذبح والسلخ وسكاكين التقطيع بانتظام", "Sanitization of slaughtering tools and knives", "CRITICAL", Decimal("20.00"), "VISUAL"),
                    ("08", "التصرف الآمن بالمخلفات الحيوانية والمصادرات ومنع دخولها للاستهلاك", "Safe disposal of condemned offal and by-products", "CRITICAL", Decimal("20.00"), "RECORD"),
                    ("09", "الختم الصحي وبطاقة التتبع للذبائح واللحوم المرسلة", "Health stamping and traceability tags on carcasses", "MAJOR", Decimal("20.00"), "DOCUMENT"),
                ],
            ),
        ],
    },
    {
        "code": "BUT",
        "name_ar": "الملاحم وتجارة اللحوم الطازجة والمبردة",
        "name_en": "Butcher Shops & Fresh/Chilled Meat",
        "activities": [
            ("FRESH_CUTS", "تقطيع وبيع اللحوم الطازجة", "Fresh Meat Cutting & Retail"),
            ("MINCED_MEAT", "فرم وتحضير اللحوم المفرومة", "Minced & Ground Meat Preparation"),
            ("POULTRY_RETAIL", "بيع وتحضير الدواجن الطازجة", "Fresh Poultry Handling & Retail"),
        ],
        "extra_sections": [
            (
                "SEC-03",
                "سلامة اللحوم الطازجة والمفرومة والدواجن وسلسلة التبريد",
                "Meat & Poultry Hygiene, Mincing Controls & Cold Chain",
                3,
                [
                    ("05", "حفظ اللحوم المبردة بين 0 و4 درجات مئوية والدواجن عند أو دون 4 درجات", "Chilled meat (0-4C) and poultry temperature control", "CRITICAL", Decimal("20.00"), "MEASUREMENT"),
                    ("06", "فصل ألواح التقطيع والسكاكين والمفارم بين اللحوم الحمراء والدواجن", "Dedicated cutting boards, knives and grinders per meat type", "CRITICAL", Decimal("20.00"), "VISUAL"),
                    ("07", "تنظيف وتبريد ماكينة الفرم وحفظ اللحوم المفرومة ضمن الشروط المحددة", "Grinder sanitation and chilled minced meat handling", "CRITICAL", Decimal("20.00"), "MEASUREMENT"),
                    ("08", "مصدر اللحوم الموثق والختم الصحي وفواتير الشراء والتتبع", "Verified meat origin, health stamp and traceability invoices", "MAJOR", Decimal("20.00"), "DOCUMENT"),
                    ("09", "عدم عرض لحوم متغيرة اللون أو الرائحة أو منتهية الصلاحية", "No spoiled, discolored or expired meat on display", "CRITICAL", Decimal("20.00"), "VISUAL"),
                ],
            ),
        ],
    },
    {
        "code": "BAK",
        "name_ar": "الأفران والمخابز والحلويات",
        "name_en": "Bakeries, Bread & Pastry",
        "activities": [
            ("BREAD_PROD", "إنتاج الخبز والمناقيش", "Bread & Dough Production"),
            ("PASTRY_CREAM", "إنتاج الحلويات والمعجنات بالكريمة", "Cream Pastry & Confectionery"),
            ("BAKING_RETAIL", "عرض وبيع المخبوزات", "Bakery Display & Retail"),
        ],
        "extra_sections": [
            (
                "SEC-03",
                "سلامة الدقيق والخميرة والكريمة وحرارة الخبز والعرض",
                "Flour/Ingredient Safety, Cream Chilling & Baking/Display",
                3,
                [
                    ("05", "تخزين الدقيق والمواد الجافة على منصات بعيدة عن الأرض والجدران والآفات", "Dry flour and ingredients stored off floor and protected from pests", "MAJOR", Decimal("20.00"), "VISUAL"),
                    ("06", "حفظ الكريمة والبيض ومنتجات الألبان المستخدمة في الحلويات مبردة (<=4°C)", "Cream, eggs and dairy kept chilled at or below 4C", "CRITICAL", Decimal("25.00"), "MEASUREMENT"),
                    ("07", "سلامة أفران الخبز والمداخن ومنع تلوث العجين بزيوت التشحيم أو الدخان", "Oven/flue condition and prevention of lubricant or smoke contamination", "MAJOR", Decimal("15.00"), "VISUAL"),
                    ("08", "تغطية وحماية المخبوزات والحلويات المعروضة ومنع ملامسة اليد المباشرة", "Protective covers on displayed baked goods and hygienic handling", "MAJOR", Decimal("20.00"), "VISUAL"),
                    ("09", "تاريخ الإنتاج والانتهاء والبطاقة الغذائية للمنتجات المعبأة والحلويات", "Production/expiry dates and labeling on packaged bakery items", "MAJOR", Decimal("20.00"), "DOCUMENT"),
                ],
            ),
        ],
    },
    {
        "code": "RST",
        "name_ar": "المطاعم والمقاهي والخدمات الغذائية",
        "name_en": "Restaurants, Cafes & Food Service",
        "activities": [
            ("HOT_KITCHEN", "المطبخ الساخن والطبخ اليومي", "Hot Kitchen & Meal Prep"),
            ("COLD_PREP", "السلطات والمقبلات والمأكولات الباردة", "Cold Prep & Ready-to-Eat"),
            ("BEV_SERVICE", "المشروبات والعصائر والخدمة", "Beverages, Juices & Service"),
        ],
        "extra_sections": [
            (
                "SEC-03",
                "الطبخ الآمن، التبريد السريع، التحضير البارد ومنع التلوث المتبادل",
                "Safe Cooking, Rapid Cooling, Cold Prep & Cross-Contamination",
                3,
                [
                    ("05", "وصول الأغذية المطبوخة إلى درجة حرارة آمنة داخلية (>=75°C) وحفظها ساخنة (>=60°C)", "Safe internal cooking (>=75C) and hot holding (>=60C)", "CRITICAL", Decimal("20.00"), "MEASUREMENT"),
                    ("06", "تبريد الأغذية المطبوخة بسرعة وحفظ الأطعمة الباردة والسلطات عند <=4°C", "Rapid cooling and cold food/salads storage at <=4C", "CRITICAL", Decimal("20.00"), "MEASUREMENT"),
                    ("07", "فصل مناطق وأدوات التحضير النيئة عن المطبوخة والجاهزة للأكل", "Separation of raw prep from cooked and ready-to-eat zones", "CRITICAL", Decimal("20.00"), "VISUAL"),
                    ("08", "غسل وتعقيم الخضار والفواكه الورقية جيداً قبل التقديم", "Thorough washing and sanitization of leafy greens and produce", "MAJOR", Decimal("20.00"), "DOCUMENT"),
                    ("09", "سلامة الزيوت المستخدمة في القلي وعدم تكرار استخدامها بعد التلف", "Frying oil quality and timely replacement", "MAJOR", Decimal("20.00"), "VISUAL"),
                ],
            ),
        ],
    },
    {
        "code": "DAI",
        "name_ar": "الألبان ومشتقات الحليب",
        "name_en": "Dairy & Milk Products",
        "activities": [
            ("PASTEURIZED_MILK", "بسترة وتعبئة الحليب", "Milk Pasteurization & Packaging"),
            ("CHEESE_LABNEH", "صناعة الجبنة واللبنة والأجبان", "Cheese, Labneh & Fermented Dairy"),
            ("DAIRY_RETAIL", "بيع منتجات الألبان المبردة", "Chilled Dairy Retail"),
        ],
        "extra_sections": [
            (
                "SEC-03",
                "البسترة الحرارية، سلامة الحليب الخام والتخمير والتبريد",
                "Pasteurization, Raw Milk Safety, Fermentation & Chilling",
                3,
                [
                    ("05", "توثيق درجات وزمن البسترة الحرارية وسلامة الحليب الخام الوارد", "Pasteurization temperature/time logs and raw milk checks", "CRITICAL", Decimal("25.00"), "RECORD"),
                    ("06", "حفظ الحليب ومشتقاته المبردة عند 0 إلى 4 درجات مئوية باستمرار", "Continuous chilled storage of milk and dairy at 0-4C", "CRITICAL", Decimal("25.00"), "MEASUREMENT"),
                    ("07", "تعقيم أوعية التخمير والتصفية والتعبئة ومنع تلوث اللبن والجبنة", "Sanitization of fermentation/straining vessels and packaging", "MAJOR", Decimal("25.00"), "VISUAL"),
                    ("08", "بطاقة البيان وتاريخ الصلاحية ورقم التشغيلة على العبوات", "Batch code, production/expiry dates and labeling", "MAJOR", Decimal("25.00"), "DOCUMENT"),
                ],
            ),
        ],
    },
    {
        "code": "SUP",
        "name_ar": "السوبرماركت ومتاجر البيع بالتجزئة",
        "name_en": "Supermarkets & Food Retail",
        "activities": [
            ("CHILLED_FROZEN", "البرادات والمجمدات الغذائية", "Chilled & Frozen Display"),
            ("DRY_PACKAGED", "المواد الجافة والمعلبات", "Dry & Packaged Goods"),
            ("DELI_COUNTER", "ركن الأجبان والمرتديلا الجاهزة", "Deli Counter & Slicing"),
        ],
        "extra_sections": [
            (
                "SEC-03",
                "مراقبة الصلاحية، البرادات والمجمدات ومنع تلوث المواد المكشوفة",
                "Expiry Control, Chillers/Freezers & Open Food Protection",
                3,
                [
                    ("05", "خلو الرفوف والبرادات من المواد منتهية الصلاحية أو التالفة أو المنتفخة", "Zero expired, damaged or bloated canned goods on shelves", "CRITICAL", Decimal("25.00"), "VISUAL"),
                    ("06", "التزام برادات العرض بالتبريد (<=4°C) والمجمدات بالتجميد (<=-18°C)", "Display chillers (<=4C) and freezers (<=-18C) compliance", "CRITICAL", Decimal("25.00"), "MEASUREMENT"),
                    ("07", "تنظيف ماكينات التقطيع في ركن الأجبان واللحوم وتغطية المنتجات المعروضة", "Deli slicer cleaning and covering exposed foods", "MAJOR", Decimal("25.00"), "VISUAL"),
                    ("08", "فصل المنظفات والمواد الكيميائية كلياً عن المواد الغذائية", "Complete separation of detergents/chemicals from food", "CRITICAL", Decimal("25.00"), "VISUAL"),
                ],
            ),
        ],
    },
    {
        "code": "SEA",
        "name_ar": "الأسماك والمنتجات البحرية",
        "name_en": "Fish & Seafood",
        "activities": [
            ("FRESH_FISH", "الأسماك الطازجة المثلجة", "Fresh Iced Fish"),
            ("SHELLFISH_PREP", "تنظيف وتجهيز الثمار البحرية", "Seafood Cleaning & Prep"),
        ],
        "extra_sections": [
            (
                "SEC-03",
                "نضارة الأسماك، الثلج الصحي ومنع فساد المنتجات البحرية",
                "Seafood Freshness, Food-Grade Ice & Spoilage Prevention",
                3,
                [
                    ("05", "حفظ الأسماك والمنتجات البحرية بالثلج الصحي أو التبريد (0 إلى 2°C)", "Iced or chilled seafood storage at 0-2C", "CRITICAL", Decimal("35.00"), "MEASUREMENT"),
                    ("06", "استخدام ثلج منتج من مياه صالحة للشرب وتصريف ماء الذوبان بعيداً عن المنتج", "Potable ice usage and proper meltwater drainage", "MAJOR", Decimal("35.00"), "VISUAL"),
                    ("07", "مؤشرات الطزاجة (العين، الخياشيم، القوام، الرائحة) وتوثيق المصدر", "Freshness indicators and origin/catch documentation", "CRITICAL", Decimal("30.00"), "DOCUMENT"),
                ],
            ),
        ],
    },
    {
        "code": "WAT",
        "name_ar": "مياه الشرب والثلج الغذائي",
        "name_en": "Drinking Water & Food Ice",
        "activities": [
            ("BOTTLED_WATER", "تعبئة ومعالجة مياه الشرب", "Bottled & Treated Water"),
            ("FOOD_ICE", "إنتاج وتوزيع الثلج الغذائي", "Edible Ice Production"),
        ],
        "extra_sections": [
            (
                "SEC-03",
                "المعالجة والترشيح والتعقيم والفحوص المخبرية للمياه والثلج",
                "Filtration, Disinfection & Microbiological/Chemical Testing",
                3,
                [
                    ("05", "انتظام مراحل الفلترة والتعقيم (أوزون/كلور/UV) وصيانة فلاتر المعالجة", "Filtration and disinfection (ozone/chlorine/UV) maintenance", "CRITICAL", Decimal("35.00"), "RECORD"),
                    ("06", "توافر نتائج الفحوص المخبرية الجرثومية والكيميائية الدورية للمياه والثلج", "Periodic lab test reports for water and ice safety", "CRITICAL", Decimal("35.00"), "DOCUMENT"),
                    ("07", "نظافة وتغطية العبوات والقوالب ومنع تلوث الثلج أثناء النقل والتوزيع", "Clean capped containers/molds and hygienic ice handling", "MAJOR", Decimal("30.00"), "VISUAL"),
                ],
            ),
        ],
    },
    {
        "code": "BEV",
        "name_ar": "العصائر والمشروبات غير الكحولية",
        "name_en": "Juices & Non-Alcoholic Beverages",
        "activities": [
            ("FRESH_JUICE", "عصر وتحضير العصائر الطازجة", "Fresh Juice Preparation"),
            ("PACKAGED_BEV", "تعبئة المشروبات والعصائر", "Beverage Bottling & Packaging"),
        ],
        "extra_sections": [
            (
                "SEC-03",
                "سلامة الفواكه والمياه والتعبئة وحفظ العصائر",
                "Fruit/Water Safety, Bottling Hygiene & Juice Chilling",
                3,
                [
                    ("05", "غسل وتعقيم الفواكه والمواد الخام قبل العصر واستخدام مياه مطابقة", "Washing/sanitizing fruits and using compliant water", "CRITICAL", Decimal("35.00"), "VISUAL"),
                    ("06", "حفظ العصائر الطازجة مبردة (<=4°C) وعدم بيع منتجات متخمرة أو منتفخة", "Chilling fresh juices (<=4C) and no fermented/bloated packs", "CRITICAL", Decimal("35.00"), "MEASUREMENT"),
                    ("07", "سلامة إحكام الإغلاق ووضوح تاريخ الصلاحية والبطاقة الغذائية", "Proper sealing, expiry date and labeling compliance", "MAJOR", Decimal("30.00"), "DOCUMENT"),
                ],
            ),
        ],
    },
    {
        "code": "OIL",
        "name_ar": "الزيوت النباتية وزيت الزيتون",
        "name_en": "Vegetable Oils & Olive Oil",
        "activities": [
            ("OLIVE_OIL", "عصر وتخزين زيت الزيتون", "Olive Oil Pressing & Storage"),
            ("REFINED_OILS", "تعبئة وتداول الزيوت النباتية", "Refined Oil Handling"),
        ],
        "extra_sections": [
            (
                "SEC-03",
                "سلامة العصر والتخزين والتعبئة ومنع الغش أو الأكسدة",
                "Pressing, Storage, Bottling & Adulteration/Oxidation Control",
                3,
                [
                    ("05", "حفظ الزيوت في عبوات/خزانات مناسبة بعيدة عن الضوء المباشر والحرارة العالية", "Storage in suitable containers away from direct light and heat", "MAJOR", Decimal("35.00"), "VISUAL"),
                    ("06", "غسل الثمار وعدم استخدام ثمار متعفنة أو متخمرة في العصر", "Washing olives/seeds and excluding moldy or fermented raw stock", "CRITICAL", Decimal("35.00"), "VISUAL"),
                    ("07", "دقة البطاقة الغذائية والبيان والصنف والمنشأ وتاريخ التعبئة والصلاحية", "Accurate labeling of grade, origin, batch and expiry dates", "MAJOR", Decimal("30.00"), "DOCUMENT"),
                ],
            ),
        ],
    },
    {
        "code": "HON",
        "name_ar": "العسل ومنتجات النحل والتمور",
        "name_en": "Honey, Bee Products & Dates",
        "activities": [
            ("HONEY_PACK", "فرز وتعبئة العسل ومنتجات النحل", "Honey Extraction & Packaging"),
            ("DATES_DRIED", "تداول التمور والفواكه المجففة", "Dates & Dried Fruits"),
        ],
        "extra_sections": [
            (
                "SEC-03",
                "سلامة الفرز والتجفيف والتخزين والبطاقة التعريفية",
                "Extraction, Drying, Storage & Labeling Integrity",
                3,
                [
                    ("05", "حماية العسل والتمور والفواكه المجففة من الرطوبة والحشرات والآفات", "Protection from moisture, insects and pests", "MAJOR", Decimal("35.00"), "VISUAL"),
                    ("06", "نظافة معدات الفرز والتعبئة وخلو العبوات من الشوائب أو التسرب", "Clean extraction/filling tools and leak-free food-grade jars", "MAJOR", Decimal("35.00"), "VISUAL"),
                    ("07", "توثيق المصدر وبيانات التعبئة والصلاحية على العبوات", "Origin records, batch details and expiry labeling", "MAJOR", Decimal("30.00"), "DOCUMENT"),
                ],
            ),
        ],
    },
    {
        "code": "MIL",
        "name_ar": "المطاحن والحبوب والبقوليات والبهارات",
        "name_en": "Mills, Grains, Legumes & Spices",
        "activities": [
            ("FLOUR_GRAIN", "طحن وتخزين الحبوب والدقيق", "Grain Milling & Flour Storage"),
            ("SPICES_LEGUMES", "تعبئة وطحن البهارات والبقوليات", "Spices & Legumes"),
        ],
        "extra_sections": [
            (
                "SEC-03",
                "مكافحة الآفات المخزنية، الرطوبة وسلامة الطحن والتعبئة",
                "Storage Pest Control, Moisture & Milling/Packing Safety",
                3,
                [
                    ("05", "خلو الحبوب والدقيق والبهارات من السوس والقوارض والعفن والرطوبة العالية", "Free from weevils, rodents, mold and excess moisture", "CRITICAL", Decimal("40.00"), "VISUAL"),
                    ("06", "نظافة المطاحن والمناخل والغرابيل وسجلات مكافحة الآفات", "Clean mills/sieves and documented pest control records", "MAJOR", Decimal("30.00"), "RECORD"),
                    ("07", "إحكام إغلاق الأكياس والعبوات ووضوح بيانات الإنتاج والانتهاء", "Sealed packaging and clear production/expiry labeling", "MAJOR", Decimal("30.00"), "DOCUMENT"),
                ],
            ),
        ],
    },
    {
        "code": "FRZ",
        "name_ar": "المستودعات والتخزين المبرد والمجمد",
        "name_en": "Cold & Frozen Warehousing",
        "activities": [
            ("COLD_STORAGE", "التخزين المبرد (0 إلى 4 مئوية)", "Chilled Storage"),
            ("FREEZER_STORAGE", "التخزين المجمد (-18 مئوية فأقل)", "Frozen Storage"),
        ],
        "extra_sections": [
            (
                "SEC-03",
                "التحكم الحراري المستمر، ترتيب التخزين وسجلات الرصد",
                "Continuous Temperature Control, Stacking & Monitoring Logs",
                3,
                [
                    ("05", "التزام غرف التبريد (0 إلى 4°C) والتجميد (<=-18°C) مع ثرمومتر معاير", "Chillers (0-4C) and freezers (<=-18C) with calibrated thermometers", "CRITICAL", Decimal("40.00"), "MEASUREMENT"),
                    ("06", "توثيق قراءات الحرارة اليومية وسجلات الأعطال أو ذوبان الجليد", "Daily temperature logs and breakdown/defrost records", "CRITICAL", Decimal("30.00"), "RECORD"),
                    ("07", "رفع الطرود عن الأرض وترك مسافات للتهوية وفصل المنتجات المتعارضة", "Pallets off floor, airflow spacing and separation of incompatible goods", "MAJOR", Decimal("30.00"), "VISUAL"),
                ],
            ),
        ],
    },
    {
        "code": "TRN",
        "name_ar": "نقل وتوزيع المواد الغذائية",
        "name_en": "Food Transport & Distribution",
        "activities": [
            ("REEFER_TRUCKS", "مركبات النقل المبردة والمجمدة", "Refrigerated Transport"),
            ("GENERAL_CARGO", "مركبات نقل المواد الجافة والمعبأة", "Dry Food Transport"),
        ],
        "extra_sections": [
            (
                "SEC-03",
                "حالة المركبات، التبريد أثناء النقل ومنع التلوث أثناء التوزيع",
                "Vehicle Condition, In-Transit Cooling & Distribution Hygiene",
                3,
                [
                    ("05", "عمل منظومة التبريد في المركبات المبردة/المجمدة قبل وبعد التحميل", "Working refrigeration prior to and during transport", "CRITICAL", Decimal("40.00"), "MEASUREMENT"),
                    ("06", "نظافة صندوق النقل وخلوه من الروائح أو المواد الكيميائية أو التسرب", "Clean cargo bay free from odors, chemicals or leaks", "CRITICAL", Decimal("30.00"), "VISUAL"),
                    ("07", "تثبيت الطرود وعدم ملامستها لأرضية المركبة وتوافر فواتير التتبع", "Secured cargo off floor and delivery/traceability manifests", "MAJOR", Decimal("30.00"), "DOCUMENT"),
                ],
            ),
        ],
    },
    {
        "code": "CAT",
        "name_ar": "التموين الغذائي والمطابخ المركزية",
        "name_en": "Catering & Central Kitchens",
        "activities": [
            ("BULK_MEALS", "إعداد الوجبات الجماعية والتموين", "Bulk Catering & Institutional Meals"),
            ("EVENT_CATERING", "تقديم الطعام للمناسبات والحفلات", "Event Catering"),
        ],
        "extra_sections": [
            (
                "SEC-03",
                "الإنتاج بكميات كبيرة، حفظ الحرارة، التتبع والاحتفاظ بالعينات",
                "Bulk Prep, Thermal Control, Traceability & Retention Samples",
                3,
                [
                    ("05", "ضبط درجات حرارة الطبخ والتبريد السريع والنقل للوجبات الجماعية", "Cooking, rapid cooling and transport temperatures for bulk meals", "CRITICAL", Decimal("35.00"), "MEASUREMENT"),
                    ("06", "توثيق التشغيلة وتواريخ التحضير وسجلات الموردين والكميات", "Batch logs, prep timestamps and supplier/quantity records", "MAJOR", Decimal("35.00"), "RECORD"),
                    ("07", "حفظ عينات مرجعية مبردة للوجبات الموردة عند الحاجة ومطابقة حاويات النقل", "Cold retention samples (where applicable) and clean transport containers", "MAJOR", Decimal("30.00"), "VISUAL"),
                ],
            ),
        ],
    },
    {
        "code": "PKG",
        "name_ar": "المواد الملامسة للغذاء والتعبئة والتغليف",
        "name_en": "Food Contact Materials & Packaging",
        "activities": [
            ("FOOD_PLASTICS", "عبوات وأكياس ملامسة للغذاء", "Food-Grade Plastics & Containers"),
            ("LABELS_WRAPS", "أغلفة وملصقات الأغذية", "Food Wraps & Packaging"),
        ],
        "extra_sections": [
            (
                "SEC-03",
                "ملاءمة المواد للغذاء، شهادات المطابقة والنظافة والتخزين",
                "Food-Grade Suitability, Compliance Certificates & Clean Storage",
                3,
                [
                    ("05", "ملاءمة المواد والعبوات والأكياس للاتصال المباشر بالغذاء وخلوها من المواد الضارة", "Food-contact suitability and absence of hazardous substances", "CRITICAL", Decimal("40.00"), "DOCUMENT"),
                    ("06", "تخزين العبوات والأغلفة في مكان نظيف وجاف ومغلق بعيداً عن الغبار والآفات", "Clean, dry, covered storage away from dust and pests", "MAJOR", Decimal("30.00"), "VISUAL"),
                    ("07", "وضوح بيانات المطابقة والتتبع والمنشأ على العبوات والملصقات", "Clear compliance, traceability and origin markings", "MAJOR", Decimal("30.00"), "DOCUMENT"),
                ],
            ),
        ],
    },
]

BASE_SECTIONS = [
    (
        "SEC-01",
        "البنية التحتية والنظافة العامة والتحكم بالآفات",
        "Infrastructure, Sanitation & Pest Control",
        1,
        [
            ("01", "سلامة الأرضيات والجدران والأسقف وسهولة تنظيفها وخلوها من التشققات", "Floors, walls & ceilings are intact, cleanable and free of cracks", "CRITICAL", Decimal("25.00"), "VISUAL"),
            ("02", "توفر مياه صالحة للشرب ونظام صرف صحي سليم ومكافحة آفات فعّالة وموثقة", "Potable water, proper drainage & effective documented pest control", "CRITICAL", Decimal("25.00"), "DOCUMENT"),
        ],
    ),
    (
        "SEC-02",
        "النظافة الشخصية، التتبع، السجلات والبطاقة الغذائية",
        "Personal Hygiene, Traceability, Records & Labeling",
        2,
        [
            ("03", "الالتزام بالنظافة الشخصية وملابس العمل الواقية والشهادات الصحية للعاملين", "Personal hygiene, protective attire & staff health certificates", "CRITICAL", Decimal("25.00"), "DOCUMENT"),
            ("04", "نظام التتبع (خطوة للخلف وخطوة للأمام) وسلامة البيانات والبطاقة الغذائية", "Traceability records and accurate food labeling/information", "MAJOR", Decimal("25.00"), "RECORD"),
        ],
    ),
]


class Command(BaseCommand):
    help = "Seed expanded LSFA sectors, sub-activities, published checklist versions, sections, and detailed items."

    def handle(self, *args, **options):
        created_sectors = 0
        created_activities = 0
        created_items = 0

        for s_data in SECTORS_CATALOG:
            sector, s_created = Sector.objects.get_or_create(
                code=s_data["code"],
                defaults={
                    "name_ar": s_data["name_ar"],
                    "name_en": s_data["name_en"],
                    "is_active": True,
                },
            )
            if s_created:
                created_sectors += 1

            act_codes = []
            for act_code, act_ar, act_en in s_data["activities"]:
                act_codes.append(act_code)
                _, a_created = SectorActivity.objects.get_or_create(
                    sector=sector,
                    code=act_code,
                    defaults={
                        "name_ar": act_ar,
                        "name_en": act_en,
                        "is_active": True,
                    },
                )
                if a_created:
                    created_activities += 1

            version, _ = ChecklistVersion.objects.get_or_create(
                sector=sector,
                version_label="1.0",
                defaults={
                    "effective_from": timezone.now().date(),
                    "is_published": True,
                    "notes": "إصدار قياسي موسّع لمكتبة LSFA القطاعية",
                },
            )
            if not version.is_published:
                version.is_published = True
                version.save(update_fields=["is_published"])

            all_sections = list(BASE_SECTIONS) + list(s_data.get("extra_sections", []))

            for sec_code, sec_ar, sec_en, sort_order, items_spec in all_sections:
                section, _ = ChecklistSection.objects.get_or_create(
                    checklist_version=version,
                    code=sec_code,
                    defaults={
                        "title_ar": sec_ar,
                        "title_en": sec_en,
                        "sort_order": sort_order,
                        "applicable_activities": act_codes,
                    },
                )

                for item_num, title_ar, title_en, severity, weight, ev_type in items_spec:
                    item_code = f"{sector.code}-{sec_code.replace('SEC-', 'S')}-{item_num}"
                    _, i_created = ChecklistItem.objects.get_or_create(
                        item_code=item_code,
                        defaults={
                            "section": section,
                            "item_number": item_num,
                            "title_ar": f"{title_ar} ({sector.name_ar})",
                            "title_en": title_en,
                            "verification_criterion": title_en,
                            "verification_method": ev_type,
                            "required_evidence": "معاينة ميدانية ومستندات/سجلات تشغيلية",
                            "raw_weight": weight,
                            "severity": severity,
                            "is_critical_item": severity == "CRITICAL",
                            "applicable_activities": act_codes,
                            "legal_reference": "قانون سلامة الغذاء اللبناني رقم 35/2015",
                            "is_active": True,
                        },
                    )
                    if i_created:
                        created_items += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Sectors added: {created_sectors}, Activities added: {created_activities}, Items added: {created_items} "
                f"(Total sectors: {Sector.objects.count()}, Total items: {ChecklistItem.objects.count()})"
            )
        )