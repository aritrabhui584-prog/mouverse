// =========================================
// RUNTIME SLIDER DYNAMIC VALUE
// =========================================

const slider = document.getElementById("runtimeSlider");
const runtimeValue = document.getElementById("runtimeValue");

if (slider && runtimeValue) {
    // Keep text updated when slider moves
    slider.addEventListener("input", () => {
        runtimeValue.innerText = slider.value;
    });
}

// =========================================
// PREMIUM LOADING OVERLAY SYSTEM
// =========================================

const filterForm = document.querySelector(".filter-section form");
const loadingOverlay = document.getElementById("loadingOverlay");

if (filterForm && loadingOverlay) {
    filterForm.addEventListener("submit", () => {
        // Store that we should scroll to recommendations after page loads
        sessionStorage.setItem("scrollToFeed", "true");
        // Activate premium glassmorphic loading screen
        loadingOverlay.classList.add("active");
    });
}

// =========================================
// AUTO-SCROLL TO FEED AFTER GENERATION
// =========================================

// Scroll to feed section if we just generated recommendations
if (sessionStorage.getItem("scrollToFeed") === "true") {
    sessionStorage.removeItem("scrollToFeed");
    // Small delay to ensure page is fully rendered
    setTimeout(() => {
        const moviesSection = document.querySelector(".movies-section");
        if (moviesSection) {
            moviesSection.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }, 300);
}

// =========================================
// SCROLL REVEAL INTERSECTION OBSERVER
// =========================================

const revealElements = document.querySelectorAll(".reveal");

if (revealElements.length > 0) {
    const revealObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("active");
                // Stop observing once animated in
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1, // Trigger when 10% of the element is visible
        rootMargin: "0px 0px -50px 0px" // Trigger slightly before entering fully
    });

    revealElements.forEach(element => {
        revealObserver.observe(element);
    });
}

// =========================================
// IMAGE ERROR HANDLING & OPTIMIZATION
// =========================================

document.addEventListener("DOMContentLoaded", () => {
    const movieImages = document.querySelectorAll(".movie-card img");
    
    movieImages.forEach(img => {
        // Add loading class
        img.style.opacity = "0.7";
        
        // Handle successful load
        img.addEventListener("load", () => {
            img.style.opacity = "1";
            img.style.transition = "opacity 0.3s ease";
        });
        
        // Handle image load errors with retry logic
        img.addEventListener("error", () => {
            console.warn(`Image failed to load: ${img.src}`);
            
            // If it's an HTTP URL, try HTTPS
            if (img.src.includes("http://") && !img.src.includes("data:")) {
                img.src = img.src.replace("http://", "https://");
                // Reset error count
                img.dataset.retries = "0";
            } else if (!img.src.includes("data:")) {
                // If HTTPS also failed, use SVG placeholder
                img.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='420'%3E%3Cdefs%3E%3ClinearGradient id='grad' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E%3Cstop offset='0%25' style='stop-color:%23001a4d;stop-opacity:1' /%3E%3Cstop offset='100%25' style='stop-color:%230f1423;stop-opacity:1' /%3E%3C/linearGradient%3E%3C/defs%3E%3Crect fill='url(%23grad)' width='300' height='420'/%3E%3Crect x='20' y='30' width='260' height='260' fill='none' stroke='%2300d9ff' stroke-width='2' opacity='0.5'/%3E%3Ctext x='150' y='160' font-size='32' fill='%2300d9ff' text-anchor='middle' font-family='Arial' font-weight='bold'%3E🎬%3C/text%3E%3Ctext x='150' y='280' font-size='12' fill='%2300d9ff' text-anchor='middle' font-family='Arial'%3EImage Unavailable%3C/text%3E%3C/svg%3E";
            }
            img.style.opacity = "1";
        });
        
        // Ensure the image is displayed if it was a data URL placeholder
        if (img.src.includes("data:image")) {
            img.style.opacity = "1";
        }
    });
});