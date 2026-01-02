// iOS 18 Inspired Interactions

document.addEventListener('DOMContentLoaded', function() {
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Add loading animation
    const cards = document.querySelectorAll('.feature-card');
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                setTimeout(() => {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }, index * 100);
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    cards.forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
        observer.observe(card);
    });

    // Header scroll effect
    let lastScroll = 0;
    const header = document.querySelector('.header');
    
    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > 100) {
            header.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
        } else {
            header.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.1)';
        }
        
        lastScroll = currentScroll;
    });
    
    // Date and Time Display
    function updateDateTime() {
        const dateDisplay = document.getElementById('date-display');
        const timeDisplay = document.getElementById('time-display');
        
        if (dateDisplay && timeDisplay) {
            const now = new Date();
            
            // Форматирование даты
            const days = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'];
            const months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 
                          'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
            
            const dayName = days[now.getDay()];
            const day = now.getDate();
            const month = months[now.getMonth()];
            const year = now.getFullYear();
            
            dateDisplay.textContent = `${dayName}, ${day} ${month} ${year}`;
            
            // Форматирование времени
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            
            timeDisplay.textContent = `${hours}:${minutes}:${seconds}`;
        }
    }
    
    // Обновляем время сразу и затем каждую секунду
    // Проверяем наличие элементов перед запуском
    const dateDisplay = document.getElementById('date-display');
    const timeDisplay = document.getElementById('time-display');
    if (dateDisplay && timeDisplay) {
        updateDateTime();
        setInterval(updateDateTime, 1000);
    }
    
    // Password toggle functionality
    const passwordToggle = document.getElementById('password-toggle');
    if (passwordToggle) {
        // Ищем input внутри контейнера пароля - берем первый input
        const passwordWrapper = passwordToggle.parentElement;
        const passwordInput = passwordWrapper.querySelector('input');
        
        if (passwordInput) {
            passwordToggle.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                // Переключаем тип поля
                if (passwordInput.type === 'password') {
                    passwordInput.type = 'text';
                    passwordToggle.classList.add('active');
                    passwordToggle.setAttribute('aria-label', 'Скрыть пароль');
                } else {
                    passwordInput.type = 'password';
                    passwordToggle.classList.remove('active');
                    passwordToggle.setAttribute('aria-label', 'Показать пароль');
                }
            });
        }
    }
});

