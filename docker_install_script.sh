#!/bin/bash

# رنگ‌ها برای نمایش بهتر
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# تابع نمایش پیام
show_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

show_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

show_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# بررسی سیستم‌عامل
detect_os() {
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        OS=$ID
        VER=$VERSION_ID
    else
        show_error "نمی‌توان سیستم‌عامل را تشخیص داد!"
        exit 1
    fi
}

# بررسی وجود Docker
check_docker() {
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | cut -d ' ' -f3 | cut -d ',' -f1)
        show_warning "Docker نسخه $DOCKER_VERSION قبلاً نصب شده است."
        read -p "آیا می‌خواهید ادامه دهید؟ (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# نصب Docker روی Ubuntu/Debian
install_docker_ubuntu() {
    show_step "نصب Docker روی Ubuntu/Debian"
    
    # آپدیت پکیج‌ها
    show_message "آپدیت لیست پکیج‌ها..."
    sudo apt update
    
    # نصب پیش‌نیازها
    show_message "نصب پیش‌نیازها..."
    sudo apt install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # اضافه کردن کلید GPG
    show_message "اضافه کردن کلید GPG Docker..."
    curl -fsSL https://download.docker.com/linux/${OS}/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # اضافه کردن مخزن
    show_message "اضافه کردن مخزن Docker..."
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/${OS} $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # آپدیت مجدد
    sudo apt update
    
    # نصب Docker
    show_message "نصب Docker Engine..."
    sudo apt install -y docker-ce docker-ce-cli containerd.io
}

# نصب Docker روی CentOS/RHEL
install_docker_centos() {
    show_step "نصب Docker روی CentOS/RHEL"
    
    # نصب yum-utils
    show_message "نصب ابزارهای مورد نیاز..."
    sudo yum install -y yum-utils
    
    # اضافه کردن مخزن Docker
    show_message "اضافه کردن مخزن Docker..."
    sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    
    # نصب Docker
    show_message "نصب Docker Engine..."
    sudo yum install -y docker-ce docker-ce-cli containerd.io
}

# نصب Docker Compose
install_docker_compose() {
    show_step "نصب Docker Compose"
    
    # دریافت آخرین نسخه
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep -Po '"tag_name": "\K.*?(?=")')
    
    show_message "دانلود Docker Compose نسخه $COMPOSE_VERSION..."
    sudo curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    
    # اعطای مجوز اجرا
    sudo chmod +x /usr/local/bin/docker-compose
    
    # ایجاد لینک symbolic
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
}

# تنظیمات بعد از نصب
post_install_setup() {
    show_step "تنظیمات بعد از نصب"
    
    # فعال‌سازی و شروع سرویس
    show_message "فعال‌سازی سرویس Docker..."
    sudo systemctl enable docker
    sudo systemctl start docker
    
    # اضافه کردن کاربر فعلی به گروه docker
    show_message "اضافه کردن کاربر $USER به گروه docker..."
    sudo usermod -aG docker $USER
    
    # تنظیم دسترسی‌ها
    sudo chown "$USER":"$USER" /home/"$USER"/.docker -R
    sudo chmod g+rwx "$HOME/.docker" -R
}

# تست نصب
test_installation() {
    show_step "تست نصب"
    
    # تست Docker
    show_message "تست Docker..."
    if docker --version; then
        show_message "✅ Docker با موفقیت نصب شد!"
    else
        show_error "❌ خطا در نصب Docker!"
        return 1
    fi
    
    # تست Docker Compose
    show_message "تست Docker Compose..."
    if docker-compose --version; then
        show_message "✅ Docker Compose با موفقیت نصب شد!"
    else
        show_error "❌ خطا در نصب Docker Compose!"
        return 1
    fi
    
    # اجرای Hello World
    show_message "تست اجرای کانتینر..."
    if docker run --rm hello-world &> /dev/null; then
        show_message "✅ Docker کاملاً کار می‌کند!"
    else
        show_warning "⚠️  ممکن است نیاز به logout/login مجدد باشد"
    fi
}

# نمایش اطلاعات مفید
show_info() {
    echo
    echo "=================================================="
    echo -e "${GREEN}🎉 نصب با موفقیت تکمیل شد!${NC}"
    echo "=================================================="
    echo
    echo "📋 اطلاعات نصب شده:"
    echo "   🐳 Docker: $(docker --version 2>/dev/null || echo 'نیاز به ری‌لاگین')"
    echo "   📦 Docker Compose: $(docker-compose --version 2>/dev/null || echo 'نیاز به ری‌لاگین')"
    echo
    echo "🚀 مراحل بعدی:"
    echo "   1. خروج و ورود مجدد: logout/login"
    echo "   2. تست نهایی: docker run hello-world"
    echo "   3. شروع استفاده: docker-compose up -d"
    echo
    echo "📖 دستورات مفید:"
    echo "   • مشاهده کانتینرها: docker ps"
    echo "   • مشاهده تصاویر: docker images"
    echo "   • پاک‌سازی: docker system prune"
    echo
    echo "🔗 مستندات بیشتر:"
    echo "   • https://docs.docker.com/"
    echo "   • https://docs.docker.com/compose/"
    echo
}

# تابع اصلی
main() {
    echo "=================================================="
    echo -e "${BLUE}🐳 اسکریپت نصب خودکار Docker${NC}"
    echo "=================================================="
    echo
    
    # بررسی دسترسی root
    if [[ $EUID -eq 0 ]]; then
        show_error "لطفاً این اسکریپت را با کاربر عادی اجرا کنید (نه root)"
        exit 1
    fi
    
    # تشخیص سیستم‌عامل
    show_step "تشخیص سیستم‌عامل"
    detect_os
    show_message "سیستم‌عامل: $OS $VER"
    
    # بررسی وجود Docker
    check_docker
    
    # نصب بر اساس سیستم‌عامل
    case $OS in
        ubuntu|debian)
            install_docker_ubuntu
            ;;
        centos|rhel|fedora)
            install_docker_centos
            ;;
        *)
            show_error "سیستم‌عامل $OS پشتیبانی نمی‌شود!"
            exit 1
            ;;
    esac
    
    # نصب Docker Compose
    install_docker_compose
    
    # تنظیمات بعد از نصب
    post_install_setup
    
    # تست نصب
    test_installation
    
    # نمایش اطلاعات
    show_info
    
    # پیام نهایی
    echo -e "${GREEN}✨ همه چیز آماده است! حالا می‌تونید از Docker استفاده کنید.${NC}"
    echo -e "${YELLOW}⚠️  توجه: ممکن است نیاز به logout/login مجدد باشد.${NC}"
}

# اجرای تابع اصلی
main "$@"