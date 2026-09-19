# راهنمای Git و GitHub

## ساخت Token
در GitHub به Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token بروید.

برای مخزن cognitive-kernel/My-ai، در Repository access همان مخزن را انتخاب کنید. برای خواندن کد Contents: Read کافی است. برای تغییر branch یا فایل، مجوز Write متناظر لازم است.

ساخت Token: https://github.com/settings/personal-access-tokens/new

## اتصال در My-AI
Repository را روی cognitive-kernel/My-ai بگذارید، Token را وارد کنید و «ذخیره و بررسی» را بزنید. Token محلی در data/.github_token نگه‌داری می‌شود و در Git commit نمی‌شود.

## خطای 404
404 در GitHub API می‌تواند یعنی repository وجود ندارد یا Token اجازه دیدن آن را ندارد. ابتدا /git/whoami را برای اعتبار Token بررسی کنید، سپس Repository access و مجوزهای Token را بررسی کنید.
