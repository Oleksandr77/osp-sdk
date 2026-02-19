# OSP Server Deployment Guide (VPS)

Цей посібник допоможе вам розгорнути OSP Server на чистому Linux сервері (Ubuntu 20.04/22.04).

## 1. Підготовка VPS

Вам потрібен сервер з публічною IP-адресою.
**Рекомендовані провайдери:**
- **Hetzner Cloud** (CPX11: ~4€/міс) — хороший баланс ціна/якісь.
- **DigitalOcean** (Basic Droplet: ~6$/міс).
- **AWS Lightsail** / **Google Cloud e2-micro**.

**Вимоги:**
- OS: Ubuntu 22.04 LTS (бажано)
- CPU: 1-2 vCPU
- RAM: 2GB+ (для Docker та Python)
- Disk: 20GB+

## 2. Підключення до сервера

Відкрийте термінал на своєму комп'ютері:

```bash
# Замініть IP_ADDRESS на адресу вашого сервера
ssh root@IP_ADDRESS
```

## 3. Копіювання файлів

Ми підготували всі необхідні файли в папці `06_Operations`. Вам потрібно скопіювати їх на сервер.
Ви можете зробити це через `scp` (secure copy) з локального терміналу (не на сервері, а на вашому комп'ютері):

```bash
# Переконайтеся, що ви в корені проекту
cd "/path/to/project"

# Скопіювати папку на сервер
scp -r 06_Operations root@IP_ADDRESS:~/osp_server_files
```

## 4. Запуск скрипта налаштування

Поверніться в SSH-сесію на сервері:

```bash
# Перейти в папку
cd ~/osp_server_files

# Зробити скрипт виконуваним
chmod +x setup_vps.sh

# Запустити автоматичне налаштування
./setup_vps.sh
```

**Що робить цей скрипт:**
- Оновлює систему.
- Встановлює Docker та Docker Compose.
- Налаштовує Firewall (UFW) для відкриття порту 8000.

## 5. Запуск OSP Server

Після успішного виконання скрипта:

```bash
# Запустити контейнери у фоновому режимі
docker compose up -d --build

# Перевірити статус
docker compose ps

# Переглянути логи
docker compose logs -f
```

## 6. Перевірка

Відкрийте у браузері або через curl:
`http://IP_ADDRESS:8000/docs` — має відкритися Swagger UI документація.

---

### Додатково: Прив'язка домену (api.amadeq.org)

Якщо ви хочете використовувати домен, вам потрібно:
1. В DNS-панелі (Cloudflare) створити `A` запис:
   - Name: `api`
   - Content: `IP_ADDRESS`
   - Proxy status: DNS Only (для початку, щоб уникнути проблем з SSL) або Proxied (якщо налаштуєте SSL).

2. Для HTTPS (Production) рекомендовано додати Nginx як reverse proxy з Let's Encrypt (Certbot).
