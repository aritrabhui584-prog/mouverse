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

// =========================================
// MOVIE DRAWER / DETAIL PANEL
// =========================================

const movieDrawer = document.getElementById('movieDrawer');
const drawerTitle = document.getElementById('drawerTitle');
const drawerPlot = document.getElementById('drawerPlot');
const drawerHeroBg = document.getElementById('drawerHeroBg');
const drawerYear = document.getElementById('drawerYear');
const drawerDuration = document.getElementById('drawerDuration');
const drawerTrailerBtn = document.getElementById('drawerTrailerBtn');
const drawerCastGrid = document.getElementById('drawerCastGrid');
const drawerSimilarGrid = document.getElementById('drawerSimilarGrid');
const drawerDirector = document.getElementById('drawerDirector');

function closeMovieDrawer() {
    if (!movieDrawer) return;
    movieDrawer.classList.remove('open');
    document.body.style.overflow = '';
    document.documentElement.style.overflow = '';
}

function openMovieDrawerFromCard(card) {
    if (!movieDrawer || !card) return;

    const title = card.dataset.title || '';
    const poster = card.dataset.poster || '';
    const year = card.dataset.year || '';
    const runtime = card.dataset.runtime || '';
    const summary = card.dataset.summary || '';
    const cast = card.dataset.cast || '';
    const director = card.dataset.director || '';
    const trailer = card.dataset.trailer || '#';

    drawerTitle.innerText = title;
    drawerPlot.innerText = summary;
    drawerYear.innerText = year;
    drawerDuration.innerText = runtime + ' min';
    drawerTrailerBtn.href = trailer;
    drawerDirector.innerText = director ? `DIRECTOR: ${director.toUpperCase()}` : '';

    // background
    if (poster) {
        drawerHeroBg.style.backgroundImage = `linear-gradient(rgba(2,6,12,0.6), rgba(2,6,12,0.6)), url('${poster}')`;
        drawerHeroBg.style.backgroundSize = 'cover';
        drawerHeroBg.style.backgroundPosition = 'center';
    } else {
        drawerHeroBg.style.backgroundImage = '';
    }

    // Cast
    drawerCastGrid.innerHTML = '';
    if (cast) {
        const members = cast.split(',').map(s => s.trim()).filter(Boolean);
        members.forEach(name => {
            const card = document.createElement('div');
            card.className = 'cast-card';
            card.innerHTML = `<div class="cast-thumb">${name.charAt(0)}</div><div class="cast-name">${name}</div>`;
            drawerCastGrid.appendChild(card);
        });
    }

    // Similar (basic placeholders)
    // Similar: find other movie cards on the page with overlapping genres
    drawerSimilarGrid.innerHTML = '';
    const allCards = Array.from(document.querySelectorAll('.movie-card'));
    const thisGenres = (card.dataset.genre || card.getAttribute('data-genre') || '').toLowerCase();

    function scoreCard(c) {
        if (c === card) return -1;
        const g = (c.dataset.genre || c.getAttribute('data-genre') || '').toLowerCase();
        let score = 0;
        if (thisGenres && g) {
            const a = thisGenres.split(',').map(s => s.trim());
            const b = g.split(',').map(s => s.trim());
            a.forEach(x => { if (b.includes(x)) score += 2; });
        }
        // small tie-breaker for rating or year (not available reliably), random small boost
        score += Math.random();
        return score;
    }

    // Rank by score and pick top 4
    const similarCandidates = allCards
        .map(c => ({ node: c, score: scoreCard(c) }))
        .filter(x => x.score >= 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, 8);

    const similarToShow = similarCandidates.slice(0, 4);
    if (similarToShow.length === 0 && allCards.length > 1) {
        // fallback: pick random other cards
        const others = allCards.filter(c => c !== card);
        for (let i = 0; i < Math.min(4, others.length); i++) {
            similarToShow.push({ node: others[i], score: 0 });
        }
    }

    similarToShow.forEach(item => {
        const node = item.node;
        const simPoster = node.dataset.poster || node.getAttribute('data-poster') || '';
        const simTitle = node.dataset.title || node.getAttribute('data-title') || 'Unknown';
        const simDiv = document.createElement('div');
        simDiv.className = 'similar-card';
        simDiv.innerHTML = `
            <button class="similar-link" type="button" aria-label="Open ${simTitle}">
                <div class="similar-thumb" style="background-image: url('${simPoster}')"></div>
                <div class="similar-title">${simTitle}</div>
            </button>`;
        // clicking a similar should open that movie in the drawer
        simDiv.querySelector('.similar-link').addEventListener('click', () => {
            openMovieDrawerFromCard(node);
        });
        drawerSimilarGrid.appendChild(simDiv);
    });

    movieDrawer.classList.add('open');
    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';
}

// Attach listeners to movie cards (if any exist)
document.addEventListener('click', (e) => {
    const card = e.target.closest('.movie-card');
    if (card) {
        openMovieDrawerFromCard(card);
    }
});

function toggleWatchlist() {
    const btn = document.getElementById('drawerWatchlistBtn');
    if (!btn) return;
    btn.classList.toggle('added');
    btn.innerText = btn.classList.contains('added') ? '✓ In Watchlist' : 'Add to Watchlist';
}

function shareMovie() {
    const title = drawerTitle ? drawerTitle.innerText : '';
    const trailer = drawerTrailerBtn ? drawerTrailerBtn.href : window.location.href;
    const shareText = `${title} — Watch trailer: ${trailer}`;
    if (navigator.share) {
        navigator.share({ title, text: shareText, url: trailer }).catch(() => {});
    } else if (navigator.clipboard) {
        navigator.clipboard.writeText(shareText).then(() => {
            alert('Movie link copied to clipboard');
        }).catch(() => {});
    } else {
        prompt('Copy this link', trailer);
    }
}

// Close when pressing Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeMovieDrawer();
});
