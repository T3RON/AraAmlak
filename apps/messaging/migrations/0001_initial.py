# Generated for phase 4A (SMS infrastructure).

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import apps.core.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('agencies', '0003_invitation'),
        ('crm', '0004_interaction_notification_task_visit'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SMSProviderConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='تاریخ به‌روزرسانی')),
                ('agency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_set', to='agencies.agency', verbose_name='آژانس')),
                ('provider', models.CharField(choices=[('kavenegar', 'کاوه‌نگار'), ('melipayamak', 'ملی‌پیامک'), ('console', 'کنسول (توسعه)'), ('fake', 'Fake (تست)')], default='console', max_length=20, verbose_name='ارائه‌دهنده')),
                ('api_key', apps.core.fields.EncryptedCharField(blank=True, max_length=500, verbose_name='کلید API')),
                ('username', models.CharField(blank=True, max_length=100, verbose_name='نام کاربری پنل')),
                ('password', apps.core.fields.EncryptedCharField(blank=True, max_length=500, verbose_name='رمز پنل')),
                ('sender_line', models.CharField(blank=True, max_length=20, verbose_name='شماره خط')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
                ('last_balance', models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True, verbose_name='آخرین اعتبار')),
                ('balance_unit', models.CharField(blank=True, max_length=10, verbose_name='واحد اعتبار')),
                ('balance_checked_at', models.DateTimeField(blank=True, null=True, verbose_name='زمان بررسی اعتبار')),
                ('last_test_ok', models.BooleanField(blank=True, null=True, verbose_name='آخرین تست موفق')),
                ('last_test_error', models.CharField(blank=True, max_length=300, verbose_name='خطای آخرین تست')),
            ],
            options={
                'verbose_name': 'تنظیمات پنل پیامک',
                'verbose_name_plural': 'تنظیمات پنل‌های پیامک',
                'constraints': [models.UniqueConstraint(fields=['agency'], name='messaging_one_sms_config_per_agency')],
            },
        ),
        migrations.CreateModel(
            name='SMSTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='تاریخ به‌روزرسانی')),
                ('agency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_set', to='agencies.agency', verbose_name='آژانس')),
                ('name', models.CharField(max_length=100, verbose_name='نام قالب')),
                ('key', models.SlugField(help_text='شناسه لاتین، مثلاً match_found', max_length=50, verbose_name='کلید')),
                ('body', models.TextField(verbose_name='متن')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
            ],
            options={
                'verbose_name': 'قالب پیامک',
                'verbose_name_plural': 'قالب‌های پیامک',
                'ordering': ['name'],
                'constraints': [models.UniqueConstraint(fields=['agency', 'key'], name='messaging_template_key_per_agency')],
            },
        ),
        migrations.CreateModel(
            name='SMSMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='تاریخ به‌روزرسانی')),
                ('agency', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sms_messages', to='agencies.agency', verbose_name='آژانس')),
                ('contact', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sms_messages', to='crm.contact', verbose_name='مخاطب')),
                ('template', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='messages', to='messaging.smstemplate', verbose_name='قالب')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_sms', to=settings.AUTH_USER_MODEL, verbose_name='ارسال‌کننده')),
                ('purpose', models.CharField(choices=[('manual', 'ارسال دستی'), ('otp', 'کد ورود'), ('match', 'اطلاع تطبیق'), ('system', 'سیستمی'), ('test', 'آزمایشی')], default='manual', max_length=10, verbose_name='نوع')),
                ('recipient', apps.core.fields.EncryptedCharField(max_length=255, verbose_name='گیرنده')),
                ('recipient_last4', models.CharField(blank=True, max_length=4, verbose_name='۴ رقم آخر گیرنده')),
                ('body', models.TextField(verbose_name='متن')),
                ('segments', models.PositiveSmallIntegerField(default=1, verbose_name='تعداد بخش')),
                ('encoding', models.CharField(blank=True, max_length=5, verbose_name='کدگذاری')),
                ('provider', models.CharField(choices=[('kavenegar', 'کاوه‌نگار'), ('melipayamak', 'ملی‌پیامک'), ('console', 'کنسول (توسعه)'), ('fake', 'Fake (تست)')], max_length=20, verbose_name='ارائه‌دهنده')),
                ('provider_message_id', models.CharField(blank=True, db_index=True, max_length=64, verbose_name='شناسه ارائه‌دهنده')),
                ('status', models.CharField(choices=[('queued', 'در صف'), ('sending', 'در حال ارسال'), ('sent', 'ارسال‌شده'), ('delivered', 'تحویل‌شده'), ('failed', 'ناموفق')], db_index=True, default='queued', max_length=10, verbose_name='وضعیت')),
                ('provider_status', models.CharField(blank=True, max_length=50, verbose_name='وضعیت خام ارائه‌دهنده')),
                ('cost_rial', models.PositiveIntegerField(blank=True, null=True, verbose_name='هزینه (ریال)')),
                ('attempts', models.PositiveSmallIntegerField(default=0, verbose_name='تعداد تلاش')),
                ('error_message', models.CharField(blank=True, max_length=300, verbose_name='خطا')),
                ('scheduled_at', models.DateTimeField(blank=True, null=True, verbose_name='زمان برنامه‌ریزی')),
                ('sent_at', models.DateTimeField(blank=True, null=True, verbose_name='زمان ارسال')),
                ('delivered_at', models.DateTimeField(blank=True, null=True, verbose_name='زمان تحویل')),
                ('failed_at', models.DateTimeField(blank=True, null=True, verbose_name='زمان شکست')),
            ],
            options={
                'verbose_name': 'پیامک',
                'verbose_name_plural': 'لاگ پیامک‌ها',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['agency', 'status', 'created_at'], name='messaging_s_agency__st_idx'), models.Index(fields=['agency', 'contact', 'created_at'], name='messaging_s_agency__ct_idx'), models.Index(fields=['status', 'sent_at'], name='messaging_s_status_sent_idx')],
            },
        ),
    ]