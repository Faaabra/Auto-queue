document.addEventListener('DOMContentLoaded', () => {
    // --- FAQ ACCORDION LOGIC ---
    const faqItems = document.querySelectorAll('.faq-item');
    
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        
        question.addEventListener('click', () => {
            const isActive = item.classList.contains('active');
            
            // Close all items
            faqItems.forEach(otherItem => {
                otherItem.classList.remove('active');
                otherItem.querySelector('.faq-answer').style.maxHeight = null;
            });
            
            // Toggle clicked item
            if (!isActive) {
                item.classList.add('active');
                const answer = item.querySelector('.faq-answer');
                answer.style.maxHeight = answer.scrollHeight + 'px';
            }
        });
    });

    // --- SCREENSHOTS GALLERY TAB LOGIC ---
    const tabBtns = document.querySelectorAll('.gallery-tab-btn');
    const imgWrappers = document.querySelectorAll('.gallery-img-wrapper');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from buttons
            tabBtns.forEach(b => b.classList.remove('active'));
            // Add active class to clicked button
            btn.classList.add('active');

            const target = btn.getAttribute('data-target');

            // Hide all images
            imgWrappers.forEach(wrapper => {
                wrapper.classList.remove('active');
            });

            // Show target image
            const targetWrapper = document.getElementById(`gallery-${target}`);
            if (targetWrapper) {
                targetWrapper.classList.add('active');
            }
        });
    });

    // --- NATIVE INTERSECTION OBSERVER FOR REVEAL ON SCROLL ---
    const revealElements = document.querySelectorAll('.reveal');
    
    const observerOptions = {
        root: null,
        threshold: 0.1, // Dispara cuando el 10% del elemento entra en pantalla
        rootMargin: '0px 0px -80px 0px' // Umbral para empezar la animación un poco antes
    };
    
    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('reveal-active');
                // Deja de observar una vez animado
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    revealElements.forEach(el => {
        observer.observe(el);
    });
});
