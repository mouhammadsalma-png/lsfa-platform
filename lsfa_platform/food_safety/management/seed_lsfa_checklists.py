from django.core.management.base import BaseCommand
from django.utils import timezone
from food_safety.models import (
    ChecklistItem,
    ChecklistSection,
    ChecklistVersion,
    Sector,
    SectorActivity,
)

SECTORS_DATA = [
    {
        "code": "REST",
        "name_ar": "المطاعم",
        "name_en": "Restaurants",
        "activities": [
            ("FULL_SERVICE", "مطعم متكامل", "Full Service Restaurant"),
            ("FAST_FOOD", "وجبات سريعة", "Fast Food"),
            ("GRILL", "مشاوي", "Grill"),
            ("SEAFOOD", "مأكولات بحرية وأسماك نيئة", "Seafood and Raw Fish"),
            ("SHAWARMA", "شاورما", "Shawarma"),
            ("TOURIST_HOTEL", "مطاعم سياحية وفندقية", "Tourist and Hotel Restaurants"),
        ],
        "sections": [
            {
                "code": "REST-01",
                "title_ar": "الموقع والبنية التحتية",
                "title_en": "Premises and Infrastructure",
                "sort_order": 1,
                "activities": [],
                "items": [
                    ("01", "سلامة موقع المؤسسة ومحيطها من مصادر التلوث", "Premises free from contamination sources", 5, "MAJOR", "VISUAL", []),
                    ("02", "سلامة الأرضيات والجدران والأسقف", "Floors, walls and ceilings maintained", 4, "MAJOR", "VISUAL", []),
                    ("03", "كفاءة أنظمة التهوية وسحب الأبخرة", "Adequate ventilation and exhaust", 4, "MODERATE", "VISUAL", []),
                    ("04", "سلامة شبكات المياه والصرف الصحي ومغاسل الأيدي", "Safe water, drainage and handwashing", 6, "MAJOR", "VISUAL", []),
                ],
            },
            {
                "code": "REST-02",
                "title_ar": "الاستلام والتخزين والتبريد",
                "title_en": "Receiving, Storage and Refrigeration",
                "sort_order": 2,
                "activities": [],
                "items": [
                    ("05", "التحقق من مصادر المواد وتواريخ الصلاحية", "Approved sources and expiry check", 6, "MAJOR", "DOCUMENT", []),
                    ("06", "ضبط درجات حرارة البرادات والمجمدات", "Refrigerator and freezer temperature control", 10, "CRITICAL", "MEASUREMENT", []),
                    ("07", "الفصل بين اللحوم النيئة والأغذية الجاهزة والمواد الكيميائية", "Raw, RTE and chemical separation", 10, "CRITICAL", "VISUAL", []),
                ],
            },
            {
                "code": "REST-03",
                "title_ar": "التحضير والطهي والتقديم والحساسية",
                "title_en": "Preparation, Cooking, Serving and Allergens",
                "sort_order": 3,
                "activities": [],
                "items": [
                    ("08", "منع التلوث المتبادل وأدوات التحضير المنفصلة", "Cross-contamination and separate tools", 10, "CRITICAL", "VISUAL", []),
                    ("09", "التحقق من درجات حرارة الطهي والحفظ الساخن والبارد", "Cooking and holding temperatures", 10, "CRITICAL", "MEASUREMENT", []),
                    ("10", "ضبط مسببات الحساسية والتتبع وسحب الأغذية", "Allergens, traceability and recall", 8, "CRITICAL", "DOCUMENT", []),
                ],
            },
            {
                "code": "REST-04",
                "title_ar": "الضوابط التخصصية للأسماك النيئة والمشاوي والشاورما",
                "title_en": "Specialized Controls: Raw Seafood, Grill and Shawarma",
                "sort_order": 4,
                "activities": ["SEAFOOD", "GRILL", "SHAWARMA"],
                "items": [
                    ("11", "ضبط سلسلة التبريد وحالة الأسماك والمأكولات البحرية النيئة", "Cold chain and raw seafood condition", 10, "CRITICAL", "MEASUREMENT", ["SEAFOOD"]),
                    ("12", "ضبط حرارة الأسياخ واللحوم المشوية ومنع النضج غير الكامل", "Skewer/grill heat control and full cooking", 10, "CRITICAL", "MEASUREMENT", ["GRILL", "SHAWARMA"]),
                ],
            },
        ],
    },
    {
        "code": "CK",
        "name_ar": "المطابخ المركزية والتموين",
        "name_en": "Central Kitchens and Catering",
        "activities": [
            ("CENTRAL_PRODUCTION", "إنتاج وجبات مركزي", "Central Meal Production"),
            ("CATERING", "تموين", "Catering"),
            ("INSTITUTIONAL_KITCHEN", "مطابخ مؤسساتية", "Institutional Kitchens"),
        ],
        "sections": [
            {
                "code": "CK-01",
                "title_ar": "البنية التحتية وتدفق العمليات",
                "title_en": "Infrastructure and Flow",
                "sort_order": 1,
                "activities": [],
                "items": [
                    ("01", "الفصل بين الأغذية النيئة والجاهزة وتحديد مسارات الحركة", "Raw/RTE separation and process flow", 10, "CRITICAL", "VISUAL", []),
                    ("02", "سلامة التهوية والمياه والصرف ومناطق التحضير", "Ventilation, water, drainage and zones", 8, "MAJOR", "VISUAL", []),
                ],
            },
            {
                "code": "CK-02",
                "title_ar": "الإنتاج والتبريد السريع والنقل",
                "title_en": "Production, Rapid Cooling and Transport",
                "sort_order": 2,
                "activities": [],
                "items": [
                    ("03", "ضبط الطهي والتبريد السريع وحفظ الوجبات", "Cooking, rapid cooling and holding", 12, "CRITICAL", "MEASUREMENT", []),
                    ("04", "ضبط حرارة النقل وتوثيق التسليم والتتبع", "Transport temperature, delivery and traceability", 10, "CRITICAL", "RECORD", []),
                ],
            },
        ],
    },
    {
        "code": "BUT",
        "name_ar": "الملاحم ومحلات تجهيز اللحوم",
        "name_en": "Butcheries and Meat Retailers",
        "activities": [
            ("BEEF", "لحوم أبقار", "Beef"),
            ("SHEEP_GOAT", "لحوم أغنام وماعز", "Sheep and Goat"),
            ("POULTRY", "دواجن", "Poultry"),
            ("MINCED_MEAT", "لحوم مفرومة ومنتجاتها", "Minced Meat and Products"),
            ("OFFAL_LIVER", "كبدة وأحشاء", "Liver and Offal"),
        ],
        "sections": [
            {
                "code": "BUT-01",
                "title_ar": "مصدر اللحوم والاستلام والتخزين",
                "title_en": "Meat Origin, Receiving and Storage",
                "sort_order": 1,
                "activities": [],
                "items": [
                    ("01", "فواتير المصدر والأختام والوثائق البيطرية والتتبع", "Invoices, veterinary stamps and traceability", 10, "CRITICAL", "DOCUMENT", []),
                    ("02", "ضبط حرارة البرادات والفصل بين اللحوم والمنتجات الأخرى", "Chiller temperatures and segregation", 10, "CRITICAL", "MEASUREMENT", []),
                ],
            },
            {
                "code": "BUT-02",
                "title_ar": "التقطيع والفرم والنظافة والمخلفات",
                "title_en": "Cutting, Mincing, Hygiene and Waste",
                "sort_order": 2,
                "activities": [],
                "items": [
                    ("03", "نظافة وتعقيم السكاكين والمناشير والمفارم ومنع خلط الأنواع", "Equipment sanitation and no undeclared mixing", 10, "CRITICAL", "VISUAL", []),
                    ("04", "النظافة الشخصية والتخلص الآمن من الدهون والعظام والمخلفات", "Hygiene and safe waste disposal", 8, "MAJOR", "VISUAL", []),
                ],
            },
            {
                "code": "BUT-03",
                "title_ar": "اشتراطات اللحوم المفرومة والكبدة والأحشاء",
                "title_en": "Minced Meat, Liver and Offal Controls",
                "sort_order": 3,
                "activities": ["MINCED_MEAT", "OFFAL_LIVER"],
                "items": [
                    ("05", "ضبط مدة وحرارة تجهيز وحفظ اللحوم المفرومة والكبدة والأحشاء", "Time/temperature control for minced meat and offal", 10, "CRITICAL", "MEASUREMENT", ["MINCED_MEAT", "OFFAL_LIVER"]),
                ],
            },
        ],
    },
    {
        "code": "SLA",
        "name_ar": "المسالخ ومراكز الذبح",
        "name_en": "Slaughterhouses",
        "activities": [
            ("CATTLE", "أبقار", "Cattle"),
            ("SHEEP", "أغنام", "Sheep"),
            ("GOATS", "ماعز", "Goats"),
            ("POULTRY", "دواجن", "Poultry"),
        ],
        "sections": [
            {
                "code": "SLA-01",
                "title_ar": "الاستقبال والفحص قبل وبعد الذبح والسلخ",
                "title_en": "Reception, Ante/Post-Mortem Inspection and Dressing",
                "sort_order": 1,
                "activities": [],
                "items": [
                    ("01", "الفحص البيطري قبل وبعد الذبح وعزل الحيوانات المريضة", "Ante/post-mortem inspection and isolation", 12, "CRITICAL", "DOCUMENT", []),
                    ("02", "منع التلوث أثناء النزف والسلخ ونزع الأحشاء وفصل المناطق", "Hygienic dressing and clean/dirty separation", 12, "CRITICAL", "VISUAL", []),
                    ("03", "عزل وإتلاف الأجزاء غير الصالحة والتبريد والتتبع بالأختام", "Condemnation, chilling and stamp traceability", 10, "CRITICAL", "RECORD", []),
                ],
            },
        ],
    },
    {
        "code": "MEAT",
        "name_ar": "مصانع اللحوم ومنتجاتها",
        "name_en": "Meat Processing Plants",
        "activities": [
            ("SAUSAGES", "نقانق", "Sausages"),
            ("BURGER", "برغر", "Burger"),
            ("DELI_MEAT", "لحوم مصنعة ومبردة", "Deli and Chilled Meat"),
        ],
        "sections": [
            {
                "code": "MEAT-01",
                "title_ar": "المواد الأولية والمعالجة الحرارية والتعبئة",
                "title_en": "Raw Materials, Thermal Processing and Packaging",
                "sort_order": 1,
                "activities": [],
                "items": [
                    ("01", "تتبع مصدر اللحوم والمضافات المسموح بها وجودة المياه", "Traceability, permitted additives and water", 10, "CRITICAL", "DOCUMENT", []),
                    ("02", "ضبط الفرم والخلط والمعالجة الحرارية ومنع التلوث المتبادل", "Mixing, thermal processing and cross-contamination", 12, "CRITICAL", "MEASUREMENT", []),
                    ("03", "سلامة العبوات والبطاقة الغذائية ورمز التشغيلة والاسترجاع", "Packaging, labelling, batch code and recall", 10, "CRITICAL", "RECORD", []),
                ],
            },
        ],
    },
    {
        "code": "FOOD",
        "name_ar": "مصانع ومعامل الصناعات الغذائية",
        "name_en": "General Food Manufacturing",
        "activities": [
            ("CANNED", "أغذية معلبة", "Canned Foods"),
            ("FROZEN", "أغذية مجمدة", "Frozen Foods"),
            ("READY_TO_EAT", "أغذية جاهزة", "Ready-to-Eat Foods"),
            ("FERMENTED", "تخمير وتفريغ هوائي", "Fermentation and Vacuum"),
        ],
        "sections": [
            {
                "code": "FOOD-01",
                "title_ar": "البنية التحتية والتصنيع والجودة والتتبع",
                "title_en": "Facility, Manufacturing, Quality and Traceability",
                "sort_order": 1,
                "activities": [],
                "items": [
                    ("01", "تصميم المنشأة وسلامة المياه ومكافحة الآفات والتنظيف والمعايرة", "Facility, water, pests, sanitation and calibration", 10, "CRITICAL", "DOCUMENT", []),
                    ("02", "ضبط التصنيع والمعالجة الحرارية ومسببات الحساسية والمضافات", "Processing, thermal control, allergens and additives", 12, "CRITICAL", "MEASUREMENT", []),
                    ("03", "التحقق المخبري والصلاحية والبطاقة الغذائية والتتبع والاسترجاع", "Lab checks, shelf-life, labelling and recall", 10, "CRITICAL", "LABORATORY", []),
                ],
            },
        ],
    },
    {
        "code": "BAK",
        "name_ar": "الأفران والمخابز",
        "name_en": "Bakeries",
        "activities": [
            ("BREAD", "خبز", "Bread"),
            ("PASTRY", "معجنات", "Pastry"),
            ("INDUSTRIAL_BAKERY", "مخابز صناعية", "Industrial Bakery"),
            ("GLUTEN_FREE", "خالٍ من الغلوتين", "Gluten-Free"),
        ],
        "sections": [
            {
                "code": "BAK-01",
                "title_ar": "المواد الأولية والخبز والتبريد والعرض",
                "title_en": "Ingredients, Baking, Cooling and Display",
                "sort_order": 1,
                "activities": [],
                "items": [
                    ("01", "سلامة الطحين والمواد الأولية والصلاحية وضبط الغلوتين والمكسرات", "Flour, ingredients, expiry and allergens", 10, "CRITICAL", "DOCUMENT", []),
                    ("02", "نظافة العجن والخبز وحماية المنتجات بعد الخبز ومنع التلوث", "Kneading, baking, post-bake protection", 10, "CRITICAL", "VISUAL", []),
                    ("03", "التبريد والتعبئة والعرض وحرارة الحشوات الحساسة والتواريخ", "Cooling, packaging, display and fillings", 8, "CRITICAL", "MEASUREMENT", []),
                ],
            },
        ],
    },
    {
        "code": "SWEET",
        "name_ar": "محلات ومصانع الحلويات",
        "name_en": "Confectionery",
        "activities": [
            ("ARABIC_SWEETS", "حلويات عربية", "Arabic Sweets"),
            ("WESTERN_PASTRY", "حلويات غربية وكريمات", "Western Pastry and Creams"),
            ("CHOCOLATE", "شوكولا", "Chocolate"),
            ("ICE_CREAM", "مثلجات", "Ice Cream"),
        ],
        "sections": [
            {
                "code": "SWEET-01",
                "title_ar": "المواد الأولية والإنتاج والتبريد والعرض",
                "title_en": "Ingredients, Production, Chilling and Display",
                "sort_order": 1,
                "activities": [],
                "items": [
                    ("01", "مصدر الحليب والقشطة والبيض والمكسرات والصلاحية ومسببات الحساسية", "Dairy, eggs, nuts, shelf-life and allergens", 10, "CRITICAL", "DOCUMENT", []),
                    ("02", "نظافة التحضير ومنع التلوث المتبادل والبيض والحشوات الحساسة", "Preparation hygiene, cross-contact and fillings", 10, "CRITICAL", "VISUAL", []),
                    ("03", "حفظ حلويات الكريمة والمثلجات مبردة/مجمدة ومنع إعادة التجميد", "Chilled/frozen confectionery and no refreezing", 10, "CRITICAL", "MEASUREMENT", []),
                ],
            },
        ],
    },
    {
        "code": "DAIRY",
        "name_ar": "معامل الألبان والأجبان",
        "name_en": "Dairy Processing",
        "activities": [
            ("RAW_MILK_PROCESSING", "حليب خام ومشتقاته", "Raw Milk and Derivatives"),
            ("SOFT_CHEESE", "أجبان طرية ولبنة", "Soft Cheese and Labneh"),
            ("AGED_CHEESE", "أجبان معتقة", "Aged Cheese"),
            ("YOGURT_ICE_CREAM", "لبن ومثلجات", "Yogurt and Ice Cream"),
        ],
        "sections": [
            {
                "code": "DAIRY-01",
                "title_ar": "استلام الحليب والبسترة والتخزين والتتبع",
                "title_en": "Milk Receiving, Pasteurization, Storage and Traceability",
                "sort_order": 1,
                "activities": [],
                "items": [
                    ("01", "مصدر الحليب وحرارة الاستلام وفحص الغش والتلوث", "Milk source, receiving temp and adulteration check", 10, "CRITICAL", "MEASUREMENT", []),
                    ("02", "ضبط البسترة أو المعالجة المعتمدة وتوثيق الزمن والحرارة", "Pasteurization and time/temperature records", 12, "CRITICAL", "RECORD", []),
                    ("03", "منع التلوث اللاحق والتبريد والفحص الميكروبي وتتبع التشغيلة", "Post-process protection, chilling, lab and recall", 10, "CRITICAL", "LABORATORY", []),
                ],
            },
        ],
    },
    {
        "code": "WATER",
        "name_ar": "مصانع المياه والمشروبات",
        "name_en": "Water and Beverage Plants",
        "activities": [
            ("BOTTLED_WATER", "مياه شرب معبأة", "Bottled Water"),
            ("SPRING_WATER", "مياه ينابيع", "Spring Water"),
            ("JUICE_BEVERAGES", "عصائر ومشروبات", "Juices and Beverages"),
        ],
        "sections": [
            {
                "code": "WATER-01",
                "title_ar": "المصدر والمعالجة والتعبئة والفحوص والتتبع",
                "title_en": "Source, Treatment, Bottling, Testing and Traceability",
                "sort_order": 1,
                "activities": [],
                "items": [
                    ("01", "مشروعية وحماية مصدر المياه وخطة التحاليل الميكروبية والكيميائية", "Water source protection and testing plan", 12, "CRITICAL", "LABORATORY", []),
                    ("02", "فعالية المعالجة والفلاتر وتعقيم العبوات وسلامة خطوط التعبئة", "Treatment, filters, bottle sanitation and filling", 12, "CRITICAL", "MEASUREMENT", []),
                    ("03", "مطابقة المنتج النهائي والتشغيلة والبطاقة وخطة الاسترجاع", "Finished product, batch coding, label and recall", 10, "CRITICAL", "DOCUMENT", []),
                ],
            },
        ],
    },
    {
        "code": "WH",
        "name_ar": "المستودعات ومراكز التخزين",
        "name_en": "Food Warehouses",
        "activities": [
            ("DRY", "تخزين جاف", "Dry Storage"),
            ("CHILLED", "تخزين مبرد", "Chilled Storage"),
            ("FROZEN", "تخزين مجمد", "Frozen Storage"),
            ("MIXED", "مستودعات مختلطة", "Mixed Storage"),
        ],
        "sections": [
            {
                "code": "WH-01",
                "title_ar": "المبنى وتنظيم المخزون والحرارة والتتبع",
                "title_en": "Premises, Stock Control, Temperature and Traceability",
                "sort_order": 1,
                "activities": [],
                "items": [
                    ("01", "سلامة المبنى ومكافحة الآفات وفصل الغذاء عن الكيماويات وعزل التالف", "Premises, pests, chemical separation and isolation", 10, "CRITICAL", "VISUAL", []),
                    ("02", "تطبيق FEFO وضبط حرارة التبريد/التجميد ومعالجة انقطاع التيار", "FEFO, cold/frozen temperatures and power backup", 10, "CRITICAL", "MEASUREMENT", []),
                    ("03", "تتبع التشغيلات والموردين والعملاء وسجلات الاسترجاع", "Batch traceability, partners and recall records", 8, "CRITICAL", "RECORD", []),
                ],
            },
        ],
    },
    {
        "code": "RET",
        "name_ar": "السوبرماركت ومتاجر بيع الغذاء",
        "name_en": "Supermarkets and Food Retail",
        "activities": [
            ("SUPERMARKET", "سوبرماركت", "Supermarket"),
            ("MINIMARKET", "ميني ماركت ومتاجر صغيرة", "Minimarket and Small Food Stores"),
            ("PRODUCE_MARKET", "أسواق خضار وفواكه", "Fruits and Vegetables Market"),
        ],
        "sections": [
            {
                "code": "RET-01",
                "title_ar": "الاستلام والعرض والتبريد والصلاحية والأقسام المتخصصة",
                "title_en": "Receiving, Display, Chilling, Expiry and Sections",
                "sort_order": 1,
                "activities": [],
                "items": [
                    ("01", "مصادر التوريد وفحص الاستلام ورفض المنتجات التالفة أو المنتهية", "Suppliers, receiving check and rejection", 10, "CRITICAL", "VISUAL", []),
                    ("02", "ضبط حرارة البرادات والمجمدات والفصل بين النيء والجاهز وحماية المكشوف", "Cold chain, separation and open food protection", 10, "CRITICAL", "MEASUREMENT", []),
                    ("03", "مراقبة تواريخ الصلاحية وسلامة العبوات ونظافة الأقسام وسحب المخالف", "Expiry dates, packaging, sections and withdrawal", 10, "CRITICAL", "RECORD", []),
                ],
            },
        ],
    },
    {
        "code": "IMP",
        "name_ar": "الاستيراد والتصدير",
        "name_en": "Food Import and Export",
        "activities": [
            ("IMPORTER", "مستورد", "Importer"),
            ("EXPORTER", "مصدر", "Exporter"),
            ("CUSTOMS_WAREHOUSE", "مستودع جمركي", "Customs Warehouse"),
        ],
        "sections": [
            {
                "code": "IMP-01",
                "title_ar": "الوثائق وفحص الشحنات والحجز والإفراج والتتبع",
                "title_en": "Documents, Consignment Check, Detention, Release and Traceability",
                "sort_order": 1,
                "activities": [],
                "items": [
                    ("01", "الشهادات الصحية والمنشأ واعتماد المنشأة ومطابقة المتطلبات", "Health/origin certificates, approval and compliance", 12, "CRITICAL", "DOCUMENT", []),
                    ("02", "سلامة الحاوية والحرارة والعبوات والصلاحية وأخذ العينات", "Container, temperature, packaging, expiry and sampling", 10, "CRITICAL", "MEASUREMENT", []),
                    ("03", "توثيق الحجز والعزل ونتائج المختبر وقرار الإفراج أو الرفض والتتبع", "Detention, lab results, release/rejection and traceability", 12, "CRITICAL", "RECORD", []),
                ],
            },
        ],
    },
    {
        "code": "TRANS",
        "name_ar": "نقل وتوزيع المواد الغذائية",
        "name_en": "Food Transport and Distribution",
        "activities": [
            ("AMBIENT", "نقل جاف", "Ambient Transport"),
            ("CHILLED", "نقل مبرد", "Chilled Transport"),
            ("FROZEN", "نقل مجمد", "Frozen Transport"),
            ("MIXED", "نقل مختلط", "Mixed Transport"),
        ],
        "sections": [
            {
                "code": "TRANS-01",
                "title_ar": "المركبات والحرارة والتوزيع والتتبع",
                "title_en": "Vehicles, Temperature, Distribution and Traceability",
                "sort_order": 1,
                "activities": [],
                "items": [
                    ("01", "ملاءمة ونظافة المركبة وحمايتها وفصل الغذاء عن المواد غير الغذائية", "Vehicle hygiene, protection and separation", 10, "CRITICAL", "VISUAL", []),
                    ("02", "التحقق الحراري قبل وأثناء النقل وتوثيق الانحرافات والإجراءات", "Pre/in-transit temperatures and deviation records", 10, "CRITICAL", "MEASUREMENT", []),
                    ("03", "توثيق المصدر والوجهة والمواعيد والسائق والمرتجعات وحالات التعطل", "Origin, destination, timing, driver and returns", 8, "MAJOR", "RECORD", []),
                ],
            },
        ],
    },
    {
        "code": "AGRI",
        "name_ar": "المزارع والإنتاج الأولي",
        "name_en": "Farms and Primary Production",
        "activities": [
            ("VEGETABLES_FRUITS", "خضار وفواكه ومزارع نباتية", "Vegetables, Fruits and Crop Farms"),
            ("LIVESTOCK", "إنتاج حيواني", "Livestock"),
            ("POULTRY_FARM", "مزارع دواجن", "Poultry Farms"),
            ("AQUACULTURE", "استزراع مائي", "Aquaculture"),
        ],
        "sections": [
            {
                "code": "AGRI-01",
                "title_ar": "المياه والمدخلات والحصاد والتعبئة",
                "title_en": "Water, Inputs, Harvest and Packing",
                "sort_order": 1,
                "activities": [],
                "items": [
                    ("01", "سلامة الموقع ومصدر وجودة مياه الري والغسل وإدارة الصرف", "Site safety, water quality and drainage", 10, "CRITICAL", "LABORATORY", []),
                    ("02", "استخدام المبيدات المسموح بها وفترات ما قبل الحصاد وتخزين الكيماويات", "Authorized pesticides, PHI and chemical storage", 12, "CRITICAL", "RECORD", []),
                    ("03", "نظافة الحصاد واستبعاد التالف وسلامة العبوات وسجلات التتبع", "Harvest hygiene, sorting, packaging and traceability", 8, "MAJOR", "VISUAL", []),
                ],
            },
            {
                "code": "AGRI-02",
                "title_ar": "اشتراطات الإنتاج الحيواني والدواجن",
                "title_en": "Livestock and Poultry Controls",
                "sort_order": 2,
                "activities": ["LIVESTOCK", "POULTRY_FARM"],
                "items": [
                    ("04", "الأدوية البيطرية وفترات السحب وعزل الحيوانات المريضة وسجلات النفوق", "Vet medicines, withdrawal periods, isolation and mortality", 12, "CRITICAL", "RECORD", ["LIVESTOCK", "POULTRY_FARM"]),
                ],
            },
        ],
    },
]


class Command(BaseCommand):
    help = "تحميل مكتبة القطاعات الـ 15 وأنشطتها الفرعية وبنود التفتيش لمنصة LSFA (إصدار 2.0)"

    def handle(self, *args, **options):
        version_label = "2.0"
        today = timezone.now().date()
        created_items = 0

        for s_data in SECTORS_DATA:
            sector, _ = Sector.objects.update_or_create(
                code=s_data["code"],
                defaults={
                    "name_ar": s_data["name_ar"],
                    "name_en": s_data["name_en"],
                    "is_active": True,
                },
            )

            for act_code, act_ar, act_en in s_data["activities"]:
                SectorActivity.objects.update_or_create(
                    sector=sector,
                    code=act_code,
                    defaults={
                        "name_ar": act_ar,
                        "name_en": act_en,
                        "is_active": True,
                    },
                )

            version, _ = ChecklistVersion.objects.update_or_create(
                sector=sector,
                version_label=version_label,
                defaults={
                    "effective_from": today,
                    "is_published": True,
                    "notes": "مكتبة الاستمارات القطاعية التشغيلية - الإصدار 2.0",
                },
            )

            for sec_data in s_data["sections"]:
                section, _ = ChecklistSection.objects.update_or_create(
                    checklist_version=version,
                    code=sec_data["code"],
                    defaults={
                        "title_ar": sec_data["title_ar"],
                        "title_en": sec_data["title_en"],
                        "sort_order": sec_data["sort_order"],
                        "applicable_activities": sec_data["activities"],
                    },
                )

                for item_num, title_ar, title_en, raw_weight, severity, method, item_acts in sec_data["items"]:
                    item_code = f"{sector.code}-{sec_data['code']}-{item_num}"
                    _, created = ChecklistItem.objects.update_or_create(
                        item_code=item_code,
                        defaults={
                            "section": section,
                            "item_number": item_num,
                            "title_ar": title_ar,
                            "title_en": title_en,
                            "verification_criterion": title_ar,
                            "verification_method": method,
                            "required_evidence": title_en,
                            "raw_weight": raw_weight,
                            "severity": severity,
                            "is_critical_item": severity == "CRITICAL",
                            "applicable_activities": item_acts,
                            "is_active": True,
                        },
                    )
                    if created:
                        created_items += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"تم تحميل {len(SECTORS_DATA)} قطاعاً (الإصدار {version_label}) وإضافة {created_items} بنداً جديداً بنجاح."
            )
        )