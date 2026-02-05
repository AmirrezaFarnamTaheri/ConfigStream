document.addEventListener('DOMContentLoaded', function() {
    console.log('Cloudflare DoH Proxy - GitHub Pages');
    
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
    
    const featureItems = document.querySelectorAll('.feature-item');
    featureItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.background = 'rgba(96, 165, 250, 0.1)';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.background = 'rgba(30, 41, 59, 0.6)';
        });
    });
});
