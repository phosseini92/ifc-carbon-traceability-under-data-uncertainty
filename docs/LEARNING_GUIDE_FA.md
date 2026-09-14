# راهنمای یادگیری و دفاع از پروژه — نسخه ۱٫۰ (اجرا و ممیزی‌شده)

## ۱. مسیر یک عدد را از ابتدا تا انتها دنبال کنید

در `outputs_v1_0_verified/element_ledger.csv` (یا در `outputs/element_ledger.csv` بعد از اجرای دوباره‌ی خودتان) یک دیوار را انتخاب کنید و این زنجیره را با دست بررسی کنید:

`GUID → IfcMaterial → mapping → contract → KBOB record UUID → NetVolume → density → factor → kg CO2e`

برای همان دیوار حجم هندسی را نیز از ابعاد کنترل کنید. هدف این است که بتوانید توضیح دهید هر عدد از کجا آمده و کدام مرحله «داده منبع»، «فرض مدل» یا «کنترل کیفیت» است.

## ۲. سه سطح اعتبار را با مثال توضیح دهید

### Structural integrity
آیا GUID، quantity، واحد، geometry و material assignment قابل خواندن و سازگار هستند؟

### Mapping integrity
آیا mapping فعال با `material_mapping_contract.json` و UUID رکورد بازبینی‌شده همخوان است؟

### Semantic validity
آیا رکورد محیط‌زیستی واقعاً برای آن ماده، فناوری، جغرافیا و boundary درست است؟

نکته کلیدی پروژه این است که دو مورد اول می‌توانند pass شوند ولی مورد سوم همچنان اشتباه باشد.

## ۳. آزمایش‌هایی که باید خودتان اجرا و توضیح دهید

۱. baseline را اجرا و نتیجه را با محاسبه دستی کنترل کنید.
۲. `missing_material` و `unmapped_material` را مقایسه کنید؛ تفاوت نوع خطا را توضیح دهید.
۳. `volume_x1000` را بررسی کنید و توضیح دهید چرا file validity به‌تنهایی این خطا را تضمین نمی‌کند.
۴. `duplicate_guid` را اجرا و ارتباط GUID با traceability را توضیح دهید.
۵. `mapping_tamper` را بررسی کنید؛ چرا review contract آن را متوقف می‌کند؟
۶. `plausible_wrong_mapping_approved` را بررسی کنید؛ چرا با وجود contract درست از نظر داخلی، نتیجه از نظر معنایی اشتباه است؟
۷. seed و تعداد sample را تغییر دهید و فرق sampling stability با model validity را توضیح دهید.
۸. `uncertainty_family_screening.csv` را بخوانید و توضیح دهید چرا این جدول variance decomposition رسمی نیست.
۹. `check_external_ifc.py` را روی fixture مستقل اجرا کنید و توضیح دهید چرا خواندن layer set مساوی پشتیبانی carbon allocation نیست.

## ۴. پرسش‌هایی که باید بدون کمک بتوانید پاسخ دهید

- چرا IFC interoperability صرفاً «فایل باز شد» نیست؟
- چرا دو representation مستقل‌تر از quantity و geometry را مقایسه می‌کنیم؟
- چرا unit consistency با semantic correctness فرق دارد؟
- mapping contract چه چیزی را تضمین می‌کند و چه چیزی را تضمین نمی‌کند؟
- چرا record UUID و source row برای provenance مهم‌اند؟
- چرا یک mapping اشتباه می‌تواند از همه کنترل‌های خودکار عبور کند؟
- چرا Monte Carlo نمی‌تواند یک mapping معنایی اشتباه را اصلاح کند؟
- چرا ranges فعلی را confidence interval ساختمان واقعی نمی‌نامیم؟
- چرا external IFC fixture به‌تنهایی general interoperability validation نیست؟
- چرا layered assembly فعلاً reject می‌شود؟
- برای اضافه‌کردن BEM دقیقاً چه model boundary و validation جدیدی لازم است؟
- برای LC3 یا earth construction چه داده‌های product/mix/context و functional comparison لازم است؟
- تفاوت این پروژه با whole-building LCA چیست؟

## ۵. توضیح کوتاه پیشنهادی برای مصاحبه

«این پروژه را برای بررسی reliability در مسیر IFC تا screening کربن ساخته‌ام. ابتدا geometry، quantity، GUID و material assignment را کنترل می‌کنم، سپس mapping فعال را با یک review contract و source UUID تطبیق می‌دهم. این کار می‌تواند خطاهای ساختاری و تغییر ناخواسته mapping را متوقف کند، اما عمداً یک آزمایش هم دارم که نشان می‌دهد اگر یک رکورد نامناسب به‌صورت داخلی و مستند تأیید شود، نرم‌افزار هنوز نمی‌تواند semantic correctness را اثبات کند. بنابراین نتیجه اصلی پروژه برای من این است که trustworthy interoperability به data traceability، release gates و review evidence نیاز دارد، نه فقط اتصال نرم‌افزارها. تحلیل uncertainty هم فقط روی فرض‌های صریح این fixture انجام می‌شود و جای validation واقعی ساختمان را نمی‌گیرد.»

این متن را حفظ نکنید؛ بعد از اجرای شخصی پروژه، آن را با زبان خودتان بازگو کنید.

## ۶. درباره کمک هوش مصنوعی

در صورت سؤال، شفاف بگویید AI-assisted coding در توسعه استفاده شده است. سپس دقیق توضیح دهید چه چیزهایی را خودتان بررسی کرده‌اید: research question، scope، source records، manual benchmark، error logic، contract logic، uncertainty assumptions، interpretation و limitations. ارزش پروژه به توان دفاع مستقل از روش و شواهد آن وابسته است، نه صرفاً وجود کد.
