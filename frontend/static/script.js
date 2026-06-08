/* ============================================================================
   MOUVERSE AI — Dashboard interactions
   ============================================================================ */

const PAGE = {
    region: document.body.dataset.region || "",
    userId: document.body.dataset.userId || "",
    userName: document.body.dataset.userName || "You",
};

const WATCHLIST_KEY = "mouverse_watchlist";

let LOCAL_POSTERS_MAP = {};

async function loadLocalPostersMap() {
    try {
        const res = await fetch("/api/posters");
        if (res.ok) {
            LOCAL_POSTERS_MAP = await res.json();
            console.log("[DEBUG] Local posters map loaded:", LOCAL_POSTERS_MAP);
        }
    } catch (err) {
        console.error("[ERROR] Failed to load local posters map:", err);
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    initPageLoader();
    initScrollReveal();
    initActiveNav();
    initSliders();
    initHeroTypewriter();
    initSmoothScroll();
    initCinematicBackground();
    initMovieCardTilt();
    
    // Load local posters map before fetching recommendation grids
    await loadLocalPostersMap();
    
    initTrendingMovies();
    initWelcomeBackSection();

    const skeleton = document.getElementById("skeletonGrid");
    if (skeleton) skeleton.style.display = "none";

    loadWatchHistory();
    fetchRecommendations(false);
});

/* ── Smooth scroll for anchor links ────────────────────────────────────────── */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                e.preventDefault();
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/* ── Page loader ─────────────────────────────────────────────────────────── */
function initPageLoader() {
    const loader = document.getElementById("pageLoader");
    if (!loader) return;
    setTimeout(() => {
        loader.classList.add("hidden");
        setTimeout(() => loader.remove(), 600);
    }, 1500);
}

/* ── Scroll reveal ───────────────────────────────────────────────────────── */
function initScrollReveal() {
    const sections = document.querySelectorAll(
        ".filter-section, .movies-section, .history-section, .section-header"
    );
    sections.forEach((el) => el.classList.add("reveal-section"));

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("visible");
                }
            });
        },
        { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    sections.forEach((el) => observer.observe(el));
}

/* ── Active nav on scroll ────────────────────────────────────────────────── */
function initActiveNav() {
    const links = document.querySelectorAll(".nav-links a[href^='#']");
    const sections = ["home", "curator", "recommendations"]
        .map((id) => document.getElementById(id))
        .filter(Boolean);

    const onScroll = () => {
        let current = "home";
        const offset = window.innerHeight * 0.35;
        sections.forEach((section) => {
            if (window.scrollY + offset >= section.offsetTop) {
                current = section.id;
            }
        });
        links.forEach((link) => {
            const href = link.getAttribute("href").slice(1);
            link.classList.toggle("active", href === current);
        });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
}

/* ── Slider live values ──────────────────────────────────────────────────── */
function initSliders() {
    const runtimeSlider = document.getElementById("runtimeSlider");
    const runtimeValue = document.getElementById("runtimeValue");
    const ratingSlider = document.getElementById("ratingSlider");
    const ratingValue = document.getElementById("ratingValue");

    if (runtimeSlider && runtimeValue) {
        runtimeSlider.addEventListener("input", () => {
            runtimeValue.textContent = runtimeSlider.value;
        });
    }
    if (ratingSlider && ratingValue) {
        ratingValue.textContent = parseFloat(ratingSlider.value).toFixed(1);
        ratingSlider.addEventListener("input", () => {
            ratingValue.textContent = parseFloat(ratingSlider.value).toFixed(1);
        });
    }
}

/* ── Hero typewriter loop ────────────────────────────────────────────────── */
function initHeroTypewriter() {
    const el = document.getElementById("typewriterText");
    if (!el) return;
    const phrases = [
        "Tailored Just For You",
        "Matched To Your Mood",
        "Curated For " + (PAGE.region || "Your Region"),
    ];
    let phraseIdx = 0;
    let charIdx = 0;
    let deleting = false;

    const tick = () => {
        const phrase = phrases[phraseIdx];
        if (!deleting) {
            charIdx++;
            el.textContent = phrase.slice(0, charIdx);
            if (charIdx === phrase.length) {
                deleting = true;
                setTimeout(tick, 2200);
                return;
            }
            setTimeout(tick, 70);
        } else {
            charIdx--;
            el.textContent = phrase.slice(0, charIdx);
            if (charIdx === 0) {
                deleting = false;
                phraseIdx = (phraseIdx + 1) % phrases.length;
                setTimeout(tick, 400);
                return;
            }
            setTimeout(tick, 35);
        }
    };
    setTimeout(tick, 1200);
}

/* ── Toast ───────────────────────────────────────────────────────────────── */
function showToast(title, message, icon = "✨") {
    const toast = document.getElementById("toastNotification");
    const tTitle = document.getElementById("toastTitle");
    const tBody = document.getElementById("toastBody");
    const tIcon = document.getElementById("toastIcon");
    if (!toast || !tTitle || !tBody || !tIcon) return;

    tTitle.textContent = title;
    tBody.textContent = message;
    tIcon.textContent = icon;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 3000);
}

function getCuratorFilters() {
    const form = document.getElementById("curatorForm");
    if (!form) return {};
    
    const mood = form.querySelector('input[name="mood"]:checked')?.value || "happy";
    const genre = form.querySelector('[name="genre"]')?.value || "Action";
    const language = form.querySelector('[name="language"]')?.value || "";
    const maxRuntime = parseInt(form.querySelector("#runtimeSlider")?.value || "240", 10);
    const minRating = parseFloat(form.querySelector("#ratingSlider")?.value || "0");
    
    // Validate runtime range
    const validatedRuntime = Math.max(30, Math.min(300, maxRuntime));
    
    // Validate rating range
    const validatedRating = Math.max(0, Math.min(10, minRating));
    
    return {
        mood,
        genre,
        language,
        maxRuntime: validatedRuntime,
        minRating: validatedRating,
    };
}

function filterMoviesClientSide(movies, filters) {
    return movies.filter((m) => {
        const rating = parseFloat(m.imdb_rating && m.imdb_rating !== "N/A" ? m.imdb_rating : m.rating) || 0;
        const runtime = parseInt(m.runtime, 10) || 0;
        // Relax filters - only filter out if runtime is way over limit
        if (runtime > filters.maxRuntime + 60) return false;
        // Rating filter is already applied on backend, keep it loose here
        if (rating < filters.minRating - 1) return false;
        return true;
    });
}

/* ── Recommendations ─────────────────────────────────────────────────────── */
let isRecommendationsRequestActive = false;
let requestTimeout = null;

const FALLBACK_MOVIES = [
    {
        "id": "fallback_1", "title": "3 Idiots", "language": "Hindi", "region": "India",
        "genre": "Comedy, Drama", "runtime": 170, "rating": 8.9, "imdb_rating": "8.9",
        "omdb_plot": "Two friends search for their long lost companion. They journey through a memory lane and find their friend who was once their inspiration.",
        "omdb_poster": "https://image.tmdb.org/t/p/w500/66A9MqXOyVFCssoloscw79z8Tew.jpg",
        "trailer_url": "https://www.youtube.com/watch?v=K0eDlFX9GMc",
        "omdb_cast": "Aamir Khan, Madhavan, Sharman Joshi",
        "omdb_director": "Rajkumar Hirani",
        "omdb_year": "2009",
        "average_review_score": 8.9,
        "review_count": 142
    },
    {
        "id": "fallback_2", "title": "Sholay", "language": "Hindi", "region": "India",
        "genre": "Action, Adventure, Drama", "runtime": 204, "rating": 9.0, "imdb_rating": "9.0",
        "omdb_plot": "A retired police officer sets out to capture a dacoit who has terrorized a village and murdered his family.",
        "omdb_poster": "https://image.tmdb.org/t/p/w500/2CAL2433ZeIihfX1CVb3bIqFqy4.jpg",
        "trailer_url": "https://www.youtube.com/watch?v=R8a0f7bYf2M",
        "omdb_cast": "Amitabh Bachchan, Dharmendra, Hema Malini",
        "omdb_director": "Ramesh Sippy",
        "omdb_year": "1975",
        "average_review_score": 9.0,
        "review_count": 98
    },
    {
        "id": "fallback_3", "title": "Zindagi Na Milegi Dobara", "language": "Hindi", "region": "India",
        "genre": "Comedy, Drama, Romance", "runtime": 155, "rating": 8.8, "imdb_rating": "8.8",
        "omdb_plot": "Three friends decide to turn their fantasy vacation into reality after one of them gets engaged.",
        "omdb_poster": "https://image.tmdb.org/t/p/w500/9VpXG0aiQF5Xb0oY9R9y9y9y9y.jpg",
        "trailer_url": "https://www.youtube.com/watch?v=KXe8y1k6qXc",
        "omdb_cast": "Hrithik Roshan, Farhan Akhtar, Abhay Deol",
        "omdb_director": "Zoya Akhtar",
        "omdb_year": "2011",
        "average_review_score": 8.8,
        "review_count": 115
    },
    {
        "id": "fallback_4", "title": "Dangal", "language": "Hindi", "region": "India",
        "genre": "Biography, Drama, Sport", "runtime": 161, "rating": 8.9, "imdb_rating": "8.9",
        "omdb_plot": "A former wrestler trains his daughters to become India's first world-class female wrestlers.",
        "omdb_poster": "https://image.tmdb.org/t/p/w500/gPbM0MK8CP8A174rmUwGsADNYKD.jpg",
        "trailer_url": "https://www.youtube.com/watch?v=x_7YlGv9u1g",
        "omdb_cast": "Aamir Khan, Fatima Sana Shaikh, Sanya Malhotra",
        "omdb_director": "Nitesh Tiwari",
        "omdb_year": "2016",
        "average_review_score": 8.9,
        "review_count": 76
    },
    {
        "id": "fallback_5", "title": "RRR", "language": "Telugu", "region": "India",
        "genre": "Action, Adventure, Drama", "runtime": 187, "rating": 8.7, "imdb_rating": "8.7",
        "omdb_plot": "A fearless revolutionary and an officer in the British force become friends and unite against the colonial oppressors.",
        "omdb_poster": "https://image.tmdb.org/t/p/w500/nEufeZlyAOLqO2brrs0yeF1lgXO.jpg",
        "trailer_url": "https://www.youtube.com/watch?v=NgBoMJy386M",
        "omdb_cast": "N.T. Rama Rao Jr., Ram Charan, Ajay Devgn",
        "omdb_director": "S.S. Rajamouli",
        "omdb_year": "2022",
        "average_review_score": 8.7,
        "review_count": 210
    },
    {
        "id": "fallback_6", "title": "Drishyam", "language": "Hindi", "region": "India",
        "genre": "Crime, Drama, Thriller", "runtime": 163, "rating": 8.9, "imdb_rating": "8.9",
        "omdb_plot": "A common man covers up a crime committed by his family to protect them from a corrupt police officer.",
        "omdb_poster": "https://image.tmdb.org/t/p/w500/vIu5Yr1d8dG7x9f8g7h6j5k4l3m2n1o0.jpg",
        "trailer_url": "https://www.youtube.com/watch?v=5XOzJH8I3L0",
        "omdb_cast": "Ajay Devgn, Tabu, Shriya Saran",
        "omdb_director": "Nishikant Kamat",
        "omdb_year": "2015",
        "average_review_score": 8.9,
        "review_count": 89
    },
    {
        "id": "fallback_7", "title": "The Dark Knight", "language": "English", "region": "International",
        "genre": "Action, Crime, Drama", "runtime": 152, "rating": 9.0, "imdb_rating": "9.0",
        "omdb_plot": "Batman raises the stakes in his war on crime. With the help of Jim Gordon and Harvey Dent, Batman sets out to dismantle the remaining criminal organizations that plague the streets.",
        "omdb_poster": "https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg",
        "trailer_url": "https://www.youtube.com/watch?v=EXeTwQWrcwY",
        "omdb_cast": "Christian Bale, Heath Ledger, Aaron Eckhart",
        "omdb_director": "Christopher Nolan",
        "omdb_year": "2008",
        "average_review_score": 9.0,
        "review_count": 512
    },
    {
        "id": "fallback_8", "title": "Inception", "language": "English", "region": "International",
        "genre": "Action, Adventure, Sci-Fi", "runtime": 148, "rating": 8.8, "imdb_rating": "8.8",
        "omdb_plot": "A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.",
        "omdb_poster": "https://image.tmdb.org/t/p/w500/9gk7admal4zl67YrxIo2AO08jXt.jpg",
        "trailer_url": "https://www.youtube.com/watch?v=YoHD9XEInc0",
        "omdb_cast": "Leonardo DiCaprio, Joseph Gordon-Levitt, Elliot Page",
        "omdb_director": "Christopher Nolan",
        "omdb_year": "2010",
        "average_review_score": 8.8,
        "review_count": 420
    },
    {
        "id": "fallback_9", "title": "The Shawshank Redemption", "language": "English", "region": "International",
        "genre": "Drama", "runtime": 142, "rating": 9.3, "imdb_rating": "9.3",
        "omdb_plot": "Over the course of several years, two convicts form a friendship, seeking consolation and, eventually, redemption through basic compassion.",
        "omdb_poster": "https://image.tmdb.org/t/p/w500/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg",
        "trailer_url": "https://www.youtube.com/watch?v=6hB3S9bIaco",
        "omdb_cast": "Tim Robbins, Morgan Freeman, Bob Gunton",
        "omdb_director": "Frank Darabont",
        "omdb_year": "1994",
        "average_review_score": 9.3,
        "review_count": 634
    },
    {
        "id": "fallback_10", "title": "Interstellar", "language": "English", "region": "International",
        "genre": "Adventure, Drama, Sci-Fi", "runtime": 169, "rating": 8.7, "imdb_rating": "8.7",
        "omdb_plot": "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.",
        "omdb_poster": "https://image.tmdb.org/t/p/w500/gEU2QniL6C8zX9U5gXN4az4K9y.jpg",
        "trailer_url": "https://www.youtube.com/watch?v=zSWdZVtXT7E",
        "omdb_cast": "Matthew McConaughey, Anne Hathaway, Jessica Chastain",
        "omdb_director": "Christopher Nolan",
        "omdb_year": "2014",
        "average_review_score": 8.7,
        "review_count": 380
    },
    {
        "id": "fallback_11", "title": "Baahubali: The Beginning", "language": "Telugu", "region": "India",
        "genre": "Action, Adventure, Drama", "runtime": 159, "rating": 8.0, "imdb_rating": "8.0",
        "omdb_plot": "A child from the Mahishmati kingdom is raised by tribal people and grows up to be a free-spirited adventurer who discovers his royal lineage.",
        "omdb_poster": "https://image.tmdb.org/t/p/w500/5Iy7m4H9K8J7L6N5M4O3P2Q1R0S.jpg",
        "trailer_url": "https://www.youtube.com/watch?v=sOEg_YZQsTI",
        "omdb_cast": "Prabhas, Rana Daggubati, Anushka Shetty",
        "omdb_director": "S.S. Rajamouli",
        "omdb_year": "2015",
        "average_review_score": 8.0,
        "review_count": 145
    },
    {
        "id": "fallback_12", "title": "Kumbalangi Nights", "language": "Malayalam", "region": "India",
        "genre": "Comedy, Drama", "runtime": 130, "rating": 8.6, "imdb_rating": "8.6",
        "omdb_plot": "The film focuses on the love-hate relationship between four brothers living in Kumbalangi and how they stand up for each other when needed.",
        "omdb_poster": "https://image.tmdb.org/t/p/w500/p1T8y8x9y0z1a2b3c4d5e6f7g8h9i0.jpg",
        "trailer_url": "https://www.youtube.com/watch?v=5XOzJH8I3L0",
        "omdb_cast": "Fahadh Faasil, Soubin Shahir, Dileesh Pothan",
        "omdb_director": "Madhu C. Narayanan",
        "omdb_year": "2019",
        "average_review_score": 8.6,
        "review_count": 54
    }
];

async function fetchRecommendations(shouldScroll = true) {
    if (isRecommendationsRequestActive) {
        console.log("[DEBUG] Request already active, skipping duplicate");
        return;
    }
    isRecommendationsRequestActive = true;

    const form = document.getElementById("curatorForm");
    if (!form) {
        isRecommendationsRequestActive = false;
        return;
    }

    const filters = getCuratorFilters();
    const skeletonGrid = document.getElementById("skeletonGrid");
    const moviesGrid = document.getElementById("moviesGrid");
    const btn = document.querySelector('.generate-btn');

    if (btn) {
        btn.classList.add('loading');
        btn.disabled = true;
    }
    if (skeletonGrid) skeletonGrid.style.display = "grid";
    if (moviesGrid) moviesGrid.style.display = "none";
    
    // Trigger Moumi thinking state
    if (window.MOUMI && typeof window.MOUMI.onThinking === 'function') {
        window.MOUMI.onThinking();
    }

    // Auto-scroll to results immediately so user sees loading state/skeletons
    if (shouldScroll) {
        const resultsSection = document.getElementById('recommendations');
        if (resultsSection) {
            resultsSection.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    }

    // Add timeout to prevent infinite loading
    requestTimeout = setTimeout(() => {
        console.error("[ERROR] Recommendation request timed out after 30 seconds");
        if (isRecommendationsRequestActive) {
            isRecommendationsRequestActive = false;
            if (skeletonGrid) skeletonGrid.style.display = "none";
            if (btn) {
                btn.classList.remove('loading');
                btn.disabled = false;
            }
            if (moviesGrid) {
                moviesGrid.style.display = "grid";
                moviesGrid.innerHTML = `
                    <div class="no-recommendations-placeholder" style="grid-column: 1 / -1; text-align: center; padding: 20px; background: rgba(255, 77, 77, 0.1); border: 1px solid rgba(255, 77, 77, 0.2); border-radius: var(--radius-md); margin-bottom: 24px;">
                        <p style="color: #ff4d4d; font-weight: bold; margin-bottom: 12px;">❌ Error: Request timed out. Please try again.</p>
                        <button type="button" class="card-action-btn primary" id="retryRecommendationsBtn" style="margin: 0 auto; display: inline-block;">🔄 Retry Fetch</button>
                        <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 12px;">Displaying fallback popular movies below to keep your movie night going!</p>
                    </div>`;

                // Add retry button handler
                const retryBtn = document.getElementById("retryRecommendationsBtn");
                if (retryBtn) {
                    retryBtn.addEventListener("click", () => fetchRecommendations(true));
                }

                // Load fallback movies
                FALLBACK_MOVIES.forEach((movie, index) => {
                    const card = createMovieCard(movie, filters.mood);
                    card.style.animationDelay = `${index * 0.08}s`;
                    moviesGrid.appendChild(card);
                    requestAnimationFrame(() => card.classList.add("visible"));
                });
                console.log(`[DEBUG] Movies rendered: ${FALLBACK_MOVIES.length} (fallback timeout)`);
            }
            showToast("Timeout", "Request took too long. Please try again.", "⏱️");
        }
    }, 30000);

    try {
        const params = new URLSearchParams({
            mood: filters.mood,
            genre: filters.genre,
            language: filters.language || "",
            min_rating: filters.minRating !== undefined ? filters.minRating : 0,
            runtime: filters.maxRuntime !== undefined ? filters.maxRuntime : 240,
            selectedRegion: PAGE.region || ""
        });
        console.log("[DEBUG] Recommendation Request Started - Params:", params.toString());
        
        const response = await fetch(`/api/recommendations?${params}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            signal: AbortSignal.timeout(25000)
        });
        
        if (!response.ok) {
            throw new Error(`Server returned status ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log("[DEBUG] Recommendation Request Completed - Success:", data.success);

        if (!moviesGrid) {
            throw new Error("Movies grid element not found");
        }
        
        moviesGrid.style.display = "grid";
        moviesGrid.classList.add("stagger-cards");
        moviesGrid.innerHTML = "";

        let movies = data.success && data.movies ? data.movies : [];
        
        if (!Array.isArray(movies)) {
            console.error("[ERROR] Invalid movies data:", movies);
            movies = [];
        }
        
        movies = filterMoviesClientSide(movies, filters);
        console.log(`[DEBUG] Movies Returned Count: ${movies.length}`);

        if (movies.length > 0) {
            movies.forEach((movie, index) => {
                const card = createMovieCard(movie, filters.mood, index);
                card.style.animationDelay = `${index * 0.08}s`;
                moviesGrid.appendChild(card);
                requestAnimationFrame(() => card.classList.add("visible"));
            });
            console.log(`[DEBUG] Movies rendered: ${movies.length}`);
            // Lazy-refresh any cards still showing default poster
            setTimeout(() => lazyRefreshDefaultPosters(), 800);
            
            // Trigger Moumi recommendation state
            if (window.MOUMI && typeof window.MOUMI.onRecommendation === 'function') {
                window.MOUMI.onRecommendation();
            }
            
            if (data.message) {
                showToast("Recommendations", data.message, "⚠️");
            } else {
                showToast("Recommendations", "🎬 Your personalized lineup is ready!", "🎬");
            }
        } else {
            moviesGrid.innerHTML = `
                <div class="no-recommendations-placeholder" style="grid-column: 1 / -1; text-align: center; padding: 20px; background: rgba(255, 212, 0, 0.1); border: 1px solid rgba(255, 212, 0, 0.2); border-radius: var(--radius-md); margin-bottom: 24px;">
                    <p style="color: #ffd400; font-weight: bold; margin-bottom: 12px;">🍿 No movies found for these filters.</p>
                    <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 12px;">Try relaxing your filters (like lowering rating or increasing runtime).</p>
                    <button type="button" class="card-action-btn primary" id="retryRecommendationsBtn" style="margin: 0 auto; display: inline-block;">🔄 Retry Search</button>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 12px;">Displaying fallback popular movies below to keep your movie night going!</p>
                </div>`;

            // Add retry button handler
            const retryBtn = document.getElementById("retryRecommendationsBtn");
            if (retryBtn) {
                retryBtn.addEventListener("click", () => fetchRecommendations(true));
            }

            // Load fallback movies
            FALLBACK_MOVIES.forEach((movie, index) => {
                const card = createMovieCard(movie, filters.mood);
                card.style.animationDelay = `${index * 0.08}s`;
                moviesGrid.appendChild(card);
                requestAnimationFrame(() => card.classList.add("visible"));
            });
            console.log(`[DEBUG] Movies rendered: ${FALLBACK_MOVIES.length} (fallback empty)`);
        }


    } catch (error) {
        console.error("[ERROR] Error fetching recommendations:", error);
        let errorMessage = "Could not fetch recommendations. Please try again.";
        
        if (error.name === 'AbortError') {
            errorMessage = "Request timed out. Please try again.";
        } else if (error.message) {
            errorMessage = error.message;
        }
        
        showToast("Fetch Failed", errorMessage, "❌");
        
        if (moviesGrid) {
            moviesGrid.style.display = "grid";
            moviesGrid.innerHTML = `
                <div class="no-recommendations-placeholder" style="grid-column: 1 / -1; text-align: center; padding: 20px; background: rgba(255, 77, 77, 0.1); border: 1px solid rgba(255, 77, 77, 0.2); border-radius: var(--radius-md); margin-bottom: 24px;">
                    <p style="color: #ff4d4d; font-weight: bold; margin-bottom: 12px;">❌ Error: ${errorMessage}</p>
                    <button type="button" class="card-action-btn primary" id="retryRecommendationsBtn" style="margin: 0 auto; display: inline-block;">🔄 Retry Fetch</button>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 12px;">Displaying fallback popular movies below to keep your movie night going!</p>
                </div>`;

            // Add retry button handler
            const retryBtn = document.getElementById("retryRecommendationsBtn");
            if (retryBtn) {
                retryBtn.addEventListener("click", () => fetchRecommendations(true));
            }

            // Load fallback movies
            FALLBACK_MOVIES.forEach((movie, index) => {
                const card = createMovieCard(movie, filters.mood);
                card.style.animationDelay = `${index * 0.08}s`;
                moviesGrid.appendChild(card);
                requestAnimationFrame(() => card.classList.add("visible"));
            });
            console.log(`[DEBUG] Movies rendered: ${FALLBACK_MOVIES.length} (fallback error)`);
        }
    } finally {
        if (requestTimeout) {
            clearTimeout(requestTimeout);
            requestTimeout = null;
        }
        if (skeletonGrid) skeletonGrid.style.display = "none";
        if (btn) {
            btn.classList.remove('loading');
            btn.disabled = false;
        }
        isRecommendationsRequestActive = false;
        console.log("[DEBUG] Recommendation request cleanup completed");
    }
}

function getRecommendations(event) {
    event.preventDefault();
    fetchRecommendations();
}

/* ── Movie cards + reviews ───────────────────────────────────────────────── */
function normalizeTitle(title) {
    if (!title) return "";
    return title.toLowerCase()
        .trim()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');
}

/**
 * Scans all movie card images on the page for default-poster.jpg.
 * For each one found, fires a /api/fetch-poster request and updates
 * the img src when a real poster URL is returned.
 */
async function lazyRefreshDefaultPosters() {
    const imgs = document.querySelectorAll(
        ".movie-card img[data-title], .history-poster-wrap img[data-title], .personalized-card img[data-title]"
    );
    const toRefresh = Array.from(imgs).filter(img => {
        const src = img.src || "";
        return src.includes("default-poster.jpg") || img.getAttribute("data-stage") === "fallback";
    });

    if (toRefresh.length === 0) return;
    console.log(`[LAZY POSTER] Refreshing ${toRefresh.length} card(s) still showing default poster`);

    for (const img of toRefresh) {
        const title = img.getAttribute("data-title") || "";
        if (!title || title === "Unknown Movie") continue;
        try {
            // Build URL from data attributes on the card element
            const card = img.closest(".movie-card, .history-item, .personalized-card");
            const year = card?.dataset?.year || "";
            const lang = card?.dataset?.lang || "";
            const mid  = card?.dataset?.movieId || "";
            const params = new URLSearchParams({ title });
            if (year) params.set("year", year);
            if (lang) params.set("lang", lang);
            if (mid)  params.set("id", mid);

            const res = await fetch(`/api/fetch-poster?${params.toString()}`);
            if (!res.ok) continue;
            const data = await res.json();
            if (data.success && data.poster_url && !data.poster_url.includes("default-poster.jpg")) {
                console.log(`[LAZY POSTER] Updated ${title} => ${data.poster_url}`);
                img.setAttribute("data-tmdb", data.poster_url);
                img.setAttribute("data-stage", "tmdb");
                img.src = data.poster_url;
            }
        } catch (e) {
            // silent — best-effort
        }
    }
}

function getLocalPosterUrl(title) {
    if (!title) return "/posters/default-poster.jpg";
    const normalized = normalizeTitle(title);
    if (LOCAL_POSTERS_MAP[normalized]) {
        return LOCAL_POSTERS_MAP[normalized];
    }
    return `/posters/${normalized}.jpg`;
}

function handlePosterLoad(img) {
    const title = img.getAttribute("data-title") || "Unknown Movie";
    const tmdbUrl = img.getAttribute("data-tmdb") || "None";
    const localUrl = img.getAttribute("data-local") || "None";
    const fallbackUrl = img.getAttribute("data-fallback") || "/posters/default-poster.jpg";
    const stage = img.getAttribute("data-stage") || "unknown";
    
    img.parentElement?.classList.remove('skeleton');
    
    const localFoundText = stage === "local" ? localUrl : (stage === "tmdb" ? "Not Needed (TMDB loaded)" : "No");
    const fallbackUsedText = stage === "fallback" ? "Yes (" + fallbackUrl + ")" : "No";

    console.log(`[DEBUG] Poster Load Success:
Movie Title: ${title}
TMDB Poster URL: ${tmdbUrl}
Local Poster Found: ${localFoundText}
Fallback Poster Used: ${fallbackUsedText}
Poster Loaded Successfully: ${img.src}
`);
}

function handlePosterError(img) {
    const title = img.getAttribute("data-title") || "Unknown Movie";
    const tmdbUrl = img.getAttribute("data-tmdb") || "None";
    const localUrl = img.getAttribute("data-local") || "None";
    const fallbackUrl = img.getAttribute("data-fallback") || "/posters/default-poster.jpg";
    const stage = img.getAttribute("data-stage") || "tmdb";
    const size = img.getAttribute("data-size") || "300x450";
    
    console.log(`[DEBUG] Poster Load Failed:
Movie Title: ${title}
TMDB Poster URL: ${tmdbUrl}
Local Poster Found: ${stage === "local" ? "Failed (" + localUrl + ")" : "N/A"}
Fallback Poster Used: ${stage === "fallback" ? "Failed (" + fallbackUrl + ")" : "N/A"}
Poster Load Failed: ${img.src}
`);

    if (stage === "tmdb") {
        img.setAttribute("data-stage", "local");
        img.src = localUrl;
    } else if (stage === "local") {
        img.setAttribute("data-stage", "fallback");
        img.src = fallbackUrl;
    } else {
        img.onerror = null;
        img.parentElement?.classList.remove('skeleton');
        img.src = `https://placehold.co/${size}/060606/00d4ff?text=${encodeURIComponent(title)}`;
    }
}

function getPosterUrl(movie) {
    const title = movie.title || "Movie";
    let poster = movie.omdb_poster || movie.poster;
    
    const isInvalid = !poster || 
        poster === "N/A" || 
        poster === "null" || 
        poster === "undefined" || 
        poster.trim() === "" || 
        poster.includes("/null") || 
        poster.includes("/undefined");
        
    if (isInvalid) {
        return getLocalPosterUrl(title);
    }
    
    if (poster.startsWith("/") && !poster.startsWith("/posters/") && !poster.startsWith("/static/")) {
        poster = `https://image.tmdb.org/t/p/w500${poster}`;
    }
    
    return poster;
}

function createMovieCard(movie, selectedMood, index = 99) {
    const card = document.createElement("article");
    card.className = "movie-card";
    card.dataset.movieId = movie.id || "";
    card.dataset.year = movie.omdb_year || "";
    card.dataset.lang = movie.language || "";

    const tmdbPoster = movie.omdb_poster || movie.poster;
    const hasTmdb = tmdbPoster && tmdbPoster !== "N/A" && tmdbPoster !== "null" && tmdbPoster !== "undefined" && tmdbPoster.trim() !== "";
    const tmdbUrl = hasTmdb ? ((tmdbPoster.startsWith("/") && !tmdbPoster.startsWith("/posters/") && !tmdbPoster.startsWith("/static/")) ? `https://image.tmdb.org/t/p/w500${tmdbPoster}` : tmdbPoster) : "";
    const localUrl = getLocalPosterUrl(movie.title);
    const initialStage = hasTmdb ? "tmdb" : "local";
    const initialSrc = hasTmdb ? tmdbUrl : localUrl;
    
    const loadingAttr = index < 4 ? "eager" : "lazy";
    const safeTitle = escapeHtml(movie.title);

    const displayRating =
        movie.imdb_rating && movie.imdb_rating !== "N/A" ? movie.imdb_rating : movie.rating;

    const langClass = (movie.language || "default").toLowerCase().replace(/\s+/g, "-");
    
    const mlScore = movie.ml_score !== undefined && movie.ml_score !== null ? Math.round(movie.ml_score * 100) : 0;
    const mlMatchDisplay = mlScore > 0 ? `<span class="ml-match-score">🤖 Match: ${mlScore}%</span>` : '';

    const userAvg = movie.average_review_score !== undefined && movie.average_review_score !== null ? movie.average_review_score : '—';
    const userCount = movie.review_count !== undefined ? movie.review_count : 0;

    card.innerHTML = `
        <div class="movie-poster-container skeleton">
            <img src="${initialSrc}" alt="${safeTitle} poster" loading="${loadingAttr}" decoding="async"
                 data-title="${safeTitle}"
                 data-tmdb="${tmdbUrl || 'None'}"
                 data-local="${localUrl}"
                 data-fallback="/posters/default-poster.jpg"
                 data-stage="${initialStage}"
                 data-size="300x450"
                 onload="handlePosterLoad(this)"
                 onerror="handlePosterError(this)">
            <span class="lang-badge lang-${langClass}">${escapeHtml(movie.language || "—")}</span>
        </div>
        <div class="movie-info-body">
            <div class="movie-card-badges">
                <span class="genre-badge">${escapeHtml(movie.genre || "")}</span>
                ${mlMatchDisplay}
            </div>
            <div class="movie-card-meta">
                <span>⭐ IMDb: ${displayRating}</span>
                <span>🕐 ${movie.runtime} min</span>
            </div>
            <div class="movie-card-reviews-meta" style="font-size: 0.78rem; color: var(--text-muted); margin-bottom: 8px;">
                <span>💬 User Avg: <strong>${userAvg} / 10</strong> (${userCount} reviews)</span>
            </div>
            <h3>${safeTitle}</h3>
            <p class="movie-card-plot">${escapeHtml(truncateText(movie.omdb_plot || "Plot unavailable.", 120))}</p>
            <div class="movie-card-actions">
                <a class="card-action-btn primary" href="${movie.trailer_url || 'https://www.youtube.com/results?search_query=' + encodeURIComponent(movie.title + ' trailer')}" target="_blank" rel="noopener">▶ Trailer</a>
                <button type="button" class="card-action-btn" data-watchlist="${escapeHtml(movie.title)}">＋ Watchlist</button>
                <button type="button" class="card-action-btn ghost" data-info='${escapeAttr(JSON.stringify(movie))}'>Info</button>
                <button type="button" class="card-action-btn" data-watch-id="${movie.id}" data-watch-title="${escapeHtml(movie.title)}">Watch</button>
            </div>
            <div class="movie-review-section" data-movie-title="${escapeHtml(movie.title)}">
                <button type="button" class="review-toggle" aria-expanded="false">
                    <span>Rate &amp; Review</span>
                    <span class="review-summary" data-summary-for="${escapeHtml(movie.title)}">No reviews yet</span>
                    <span class="review-chevron">▼</span>
                </button>
                <div class="review-panel" hidden>
                    <div class="review-avg-block" data-avg-for="${escapeHtml(movie.title)}"></div>
                    <div class="review-stars-input" data-title="${escapeHtml(movie.title)}" role="group" aria-label="Your rating">
                        ${[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => `<button type="button" class="review-star" data-value="${n}" aria-label="${n} stars" style="font-size: 1.1rem; padding: 0 1px;">★</button>`).join("")}
                    </div>
                    <textarea class="review-textarea" placeholder="Share your thoughts..." rows="3"></textarea>
                    <button type="button" class="review-submit-btn">Submit Review</button>
                    <div class="reviews-list" data-list-for="${escapeHtml(movie.title)}"></div>
                </div>
            </div>
        </div>
    `;

    card.querySelector("[data-info]")?.addEventListener("click", (e) => {
        openMovieDrawer(JSON.parse(e.currentTarget.dataset.info));
    });
    card.querySelector("[data-watchlist]")?.addEventListener("click", (e) => {
        toggleWatchlist(e.currentTarget.dataset.watchlist);
    });
    card.querySelector("[data-watch-id]")?.addEventListener("click", (e) => {
        markWatched(
            String(e.currentTarget.dataset.watchId),
            e.currentTarget.dataset.watchTitle,
            selectedMood
        );
    });

    initReviewSection(card, movie, index);
    return card;
}

function truncateText(text, max) {
    if (!text || text.length <= max) return text;
    return text.slice(0, max).trim() + "…";
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function escapeAttr(str) {
    return String(str).replace(/'/g, "&#39;");
}

function escapeQuote(str) {
    return str.replace(/'/g, "\\'");
}

/* ── Reviews API ─────────────────────────────────────────────────────────── */
function initReviewSection(card, movie, cardIndex = 0) {
    const section = card.querySelector(".movie-review-section");
    if (!section) return;

    const movieTitle = movie.title;
    const movieId = movie.id;

    const toggle = section.querySelector(".review-toggle");
    const panel = section.querySelector(".review-panel");
    const starsWrap = section.querySelector(".review-stars-input");
    const submitBtn = section.querySelector(".review-submit-btn");
    const textarea = section.querySelector(".review-textarea");

    // Stagger review loads: first card immediately, others delayed by index to avoid DB overload
    const delay = Math.min(cardIndex * 200, 3000);
    setTimeout(() => loadReviewsForMovie(movieTitle), delay);

    toggle?.addEventListener("click", async () => {
        const open = toggle.getAttribute("aria-expanded") === "true";
        toggle.setAttribute("aria-expanded", String(!open));
        panel.hidden = open;
        section.classList.toggle("open", !open);
        if (!open) await loadReviewsForMovie(movieTitle);
    });

    starsWrap?.querySelectorAll(".review-star").forEach((star) => {
        star.addEventListener("mouseenter", () => highlightReviewStars(starsWrap, parseInt(star.dataset.value, 10)));
        star.addEventListener("mouseleave", () => {
            const currentSelected = parseInt(section.dataset.selectedStars || "0", 10);
            highlightReviewStars(starsWrap, currentSelected);
        });
        star.addEventListener("click", () => {
            const val = parseInt(star.dataset.value, 10);
            section.dataset.selectedStars = val;
            highlightReviewStars(starsWrap, val);
        });
    });

    submitBtn?.addEventListener("click", async () => {
        const selectedStars = parseInt(section.dataset.selectedStars || "0", 10);
        if (!selectedStars) {
            showToast("Review", "Please select a star rating first.", "⭐");
            return;
        }
        
        const editReviewId = submitBtn.dataset.editReviewId;
        
        try {
            const bodyData = {
                movie_title: movieTitle,
                movie_id: movieId,
                stars: selectedStars,
                review_text: textarea.value.trim(),
                user_id: PAGE.userId,
                region: PAGE.region,
            };
            if (editReviewId) {
                bodyData.review_id = editReviewId;
            }

            const res = await fetch("/submit-review", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(bodyData),
            });
            const data = await res.json();
            if (data.success) {
                showToast(editReviewId ? "Review updated!" : "Review submitted!", "✅ Review saved successfully.", "✅");
                textarea.value = "";
                section.dataset.selectedStars = "0";
                highlightReviewStars(starsWrap, 0);
                submitBtn.textContent = "Submit Review";
                delete submitBtn.dataset.editReviewId;
                
                const cancelBtn = section.querySelector(".review-cancel-btn");
                if (cancelBtn) cancelBtn.remove();
                
                await loadReviewsForMovie(movieTitle);
            } else {
                showToast("Error", data.error || "Could not submit review.", "❌");
            }
        } catch (err) {
            console.error(err);
            showToast("Error", "Could not submit review.", "❌");
        }
    });
}

function highlightReviewStars(container, value) {
    container.querySelectorAll(".review-star").forEach((s) => {
        s.classList.toggle("active", parseInt(s.dataset.value, 10) <= value);
    });
}

async function loadReviewsForMovie(movieTitle) {
    const summaryEls = document.querySelectorAll(`[data-summary-for="${CSS.escape(movieTitle)}"]`);
    const avgEls = document.querySelectorAll(`[data-avg-for="${CSS.escape(movieTitle)}"]`);
    const listEls = document.querySelectorAll(`[data-list-for="${CSS.escape(movieTitle)}"]`);

    summaryEls.forEach((el) => {
        if (!el.querySelector('.review-retry-link')) {
            el.textContent = "Loading…";
        }
    });

    try {
        const res = await fetch(
            `/get-reviews?title=${encodeURIComponent(movieTitle)}&region=${encodeURIComponent(PAGE.region)}`,
            { signal: AbortSignal.timeout(8000) }
        );
        
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        
        const data = await res.json();

        if (data.success) {
            const summaryText = data.review_count > 0
                ? `★ ${data.average_rating} (${data.review_count} reviews)`
                : "No Reviews Yet";

            summaryEls.forEach((el) => {
                el.textContent = summaryText;
            });
            
            avgEls.forEach((el) => {
                if (!data.review_count) {
                    el.innerHTML = "<p class=\"review-avg-empty\">Be the first to review!</p>";
                    return;
                }
                el.innerHTML = `<p class="review-avg">Average: <strong>★ ${data.average_rating} / 10</strong> · ${data.review_count} review(s)</p>`;
            });

            listEls.forEach((listEl) => {
                listEl.innerHTML = "";
                if (!data.reviews?.length) {
                    listEl.innerHTML = '<p class="review-empty">No reviews yet for this title.</p>';
                    return;
                }
                data.reviews.forEach((review) => {
                    listEl.appendChild(renderReviewItem(review, movieTitle));
                });
            });
        } else {
            throw new Error(data.error || "Failed loading reviews");
        }
    } catch (err) {
        console.error(`Reviews load error for ${movieTitle}:`, err);
        
        summaryEls.forEach((el) => {
            el.innerHTML = `No Reviews Yet <span class="review-retry-link" style="color: var(--cyan); text-decoration: underline; margin-left: 6px; cursor: pointer;" role="button">Retry</span>`;
            
            const retryBtn = el.querySelector(".review-retry-link");
            if (retryBtn) {
                retryBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    loadReviewsForMovie(movieTitle);
                });
            }
        });

        avgEls.forEach((el) => {
            el.innerHTML = "<p class=\"review-avg-empty\">Reviews temporary unavailable. Click retry above.</p>";
        });
    }
}

function renderReviewItem(review, movieTitle) {
    const item = document.createElement("div");
    item.className = "review-item";
    const initial = (review.user_name || "?").charAt(0).toUpperCase();
    const date = formatReviewDate(review.created_at);
    const stars = "★".repeat(review.stars) + "☆".repeat(10 - review.stars);

    const isOwner = String(review.user_id) === String(PAGE.userId);
    let ownerActions = "";
    if (isOwner) {
        ownerActions = `
            <div class="review-owner-actions" style="margin-top: 6px; display: flex; gap: 8px;">
                <button type="button" class="review-edit-btn" style="background:none; border:none; color:var(--cyan); cursor:pointer; font-size:0.75rem; padding:0;">✏️ Edit</button>
                <button type="button" class="review-delete-btn" style="background:none; border:none; color:#ff4d4d; cursor:pointer; font-size:0.75rem; padding:0;">🗑️ Delete</button>
            </div>
        `;
    }

    item.innerHTML = `
        <div class="review-item-header">
            <span class="review-avatar" aria-hidden="true">${escapeHtml(initial)}</span>
            <div>
                <strong>${escapeHtml(review.user_name)}</strong>
                <span class="region-badge review-region">${escapeHtml(review.region || "")}</span>
            </div>
            <span class="review-date">${date}</span>
        </div>
        <div class="review-stars-display" aria-label="${review.stars} out of 10 stars" style="font-size:0.8rem; letter-spacing:1px;">${stars}</div>
        <p class="review-body" style="font-size:0.85rem; margin: 4px 0; color:var(--text-primary);">${escapeHtml(review.review_text || "")}</p>
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <button type="button" class="review-helpful-btn" data-review-id="${review.id}">
                👍 Helpful (${review.helpful_count || 0})
            </button>
            ${ownerActions}
        </div>
    `;

    item.querySelector(".review-helpful-btn")?.addEventListener("click", async (e) => {
        const btn = e.currentTarget;
        const reviewId = btn.dataset.reviewId;
        try {
            const res = await fetch("/submit-review", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ helpful_review_id: reviewId }),
            });
            const data = await res.json();
            if (data.success) {
                const count = parseInt(btn.textContent.match(/\d+/)?.[0] || "0", 10) + 1;
                btn.textContent = `👍 Helpful (${count})`;
            }
        } catch (err) {
            console.error(err);
        }
    });

    if (isOwner) {
        item.querySelector(".review-edit-btn")?.addEventListener("click", () => {
            const section = item.closest(".movie-review-section");
            if (!section) return;
            
            const textarea = section.querySelector(".review-textarea");
            const starsWrap = section.querySelector(".review-stars-input");
            const submitBtn = section.querySelector(".review-submit-btn");
            
            if (textarea && starsWrap && submitBtn) {
                textarea.value = review.review_text;
                textarea.focus();
                
                section.dataset.selectedStars = review.stars;
                highlightReviewStars(starsWrap, review.stars);
                
                submitBtn.textContent = "Save Review";
                submitBtn.dataset.editReviewId = review.id;
                
                let cancelBtn = section.querySelector(".review-cancel-btn");
                if (!cancelBtn) {
                    cancelBtn = document.createElement("button");
                    cancelBtn.type = "button";
                    cancelBtn.className = "review-cancel-btn";
                    cancelBtn.textContent = "Cancel";
                    cancelBtn.style.cssText = "margin-top: 6px; width: 100%; padding: 8px; background: rgba(255,255,255,0.1); color: #fff; border: none; border-radius: var(--radius-sm); font-weight: 700; cursor: pointer; transition: var(--transition-fast);";
                    cancelBtn.addEventListener("click", () => {
                        textarea.value = "";
                        highlightReviewStars(starsWrap, 0);
                        section.dataset.selectedStars = "0";
                        delete submitBtn.dataset.editReviewId;
                        submitBtn.textContent = "Submit Review";
                        cancelBtn.remove();
                    });
                    submitBtn.after(cancelBtn);
                }
            }
        });
        
        item.querySelector(".review-delete-btn")?.addEventListener("click", async () => {
            if (!confirm("Are you sure you want to delete this review?")) return;
            try {
                const res = await fetch("/delete-review", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ review_id: review.id })
                });
                const data = await res.json();
                if (data.success) {
                    showToast("Review deleted", "🗑️ Your review has been removed.", "🗑️");
                    await loadReviewsForMovie(movieTitle);
                } else {
                    showToast("Error", data.error || "Could not delete review.", "❌");
                }
            } catch (err) {
                console.error(err);
                showToast("Error", "Could not delete review.", "❌");
            }
        });
    }

    return item;
}

function formatReviewDate(iso) {
    if (!iso) return "";
    try {
        return new Date(iso).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
        });
    } catch {
        return iso;
    }
}

/* ── Watchlist (local) ───────────────────────────────────────────────────── */
function getWatchlist() {
    try {
        return JSON.parse(localStorage.getItem(WATCHLIST_KEY) || "[]");
    } catch {
        return [];
    }
}

function toggleWatchlist(title) {
    let list = getWatchlist();
    if (list.includes(title)) {
        list = list.filter((t) => t !== title);
        showToast("Watchlist", `Removed "${title}" from watchlist.`, "📋");
    } else {
        list.push(title);
        showToast("Added to Watchlist!", `✅ "${title}" saved for later.`, "✅");
    }
    localStorage.setItem(WATCHLIST_KEY, JSON.stringify(list));
}

/* ── Movie drawer ──────────────────────────────────────────────────────────── */
function openMovieDrawer(movie) {
    const drawer = document.getElementById("movieDrawer");
    if (!drawer) return;

    document.getElementById("drawerTitle").textContent = movie.title;
    document.getElementById("drawerPlot").textContent = movie.omdb_plot || "";
    document.getElementById("drawerYear").textContent =
        movie.omdb_year && movie.omdb_year !== "N/A" ? movie.omdb_year : "N/A";
    document.getElementById("drawerDuration").textContent = `${movie.runtime} min`;
    document.getElementById("drawerRating").textContent = `⭐ ${
        movie.imdb_rating && movie.imdb_rating !== "N/A" ? movie.imdb_rating : movie.rating
    }`;
    document.getElementById("drawerDirector").textContent =
        movie.omdb_director && movie.omdb_director !== "N/A" ? movie.omdb_director : "N/A";
    document.getElementById("drawerCast").textContent =
        movie.omdb_cast && movie.omdb_cast !== "N/A" ? movie.omdb_cast : "N/A";
    document.getElementById("drawerGenre").textContent = movie.genre || "";
    document.getElementById("drawerLanguage").textContent = movie.language || "";

    const tmdbPoster = movie.omdb_poster || movie.poster;
    const hasTmdb = tmdbPoster && tmdbPoster !== "N/A" && tmdbPoster !== "null" && tmdbPoster !== "undefined" && tmdbPoster.trim() !== "";
    const tmdbUrl = hasTmdb ? (tmdbPoster.startsWith("/") ? `https://image.tmdb.org/t/p/w500${tmdbPoster}` : tmdbPoster) : "";
    const localUrl = getLocalPosterUrl(movie.title);
    const fallbackUrl = "/posters/default-poster.jpg";
    const drawerBg = document.getElementById("drawerHeroBg");
    
    if (drawerBg) {
        const title = movie.title || "Movie";
        const initialStage = hasTmdb ? "tmdb" : "local";
        const initialSrc = hasTmdb ? tmdbUrl : localUrl;
        
        drawerBg.style.backgroundImage = `url('${initialSrc}')`;
        
        // Setup image helper to handle preloading and fallbacks
        const img = new Image();
        img.src = initialSrc;
        
        img.onload = () => {
            drawerBg.style.backgroundImage = `url('${img.src}')`;
            const localFoundText = initialStage === "local" ? localUrl : (initialStage === "tmdb" ? "Not Needed (TMDB loaded)" : "No");
            const fallbackUsedText = initialStage === "fallback" ? "Yes (" + fallbackUrl + ")" : "No";
            
            console.log(`[DEBUG] Drawer Poster Load Success:
Movie Title: ${title}
TMDB Poster URL: ${tmdbUrl || 'None'}
Local Poster Found: ${localFoundText}
Fallback Poster Used: ${fallbackUsedText}
Poster Loaded Successfully: ${img.src}
`);
        };
        
        img.onerror = () => {
            console.log(`[DEBUG] Drawer Poster Load Failed:
Movie Title: ${title}
TMDB Poster URL: ${tmdbUrl || 'None'}
Local Poster Found: ${initialStage === "local" ? "Failed (" + localUrl + ")" : "N/A"}
Fallback Poster Used: ${initialStage === "fallback" ? "Failed (" + fallbackUrl + ")" : "N/A"}
Poster Load Failed: ${img.src}
`);
            if (initialStage === "tmdb") {
                const imgLocal = new Image();
                imgLocal.src = localUrl;
                drawerBg.style.backgroundImage = `url('${localUrl}')`;
                imgLocal.onload = () => {
                    drawerBg.style.backgroundImage = `url('${localUrl}')`;
                    console.log(`[DEBUG] Drawer Poster Load Success:
Movie Title: ${title}
TMDB Poster URL: ${tmdbUrl}
Local Poster Found: Yes (${localUrl})
Fallback Poster Used: No
Poster Loaded Successfully: ${localUrl}
`);
                };
                imgLocal.onerror = () => {
                    console.log(`[DEBUG] Drawer Poster Load Failed:
Movie Title: ${title}
TMDB Poster URL: ${tmdbUrl}
Local Poster Found: Failed (${localUrl})
Fallback Poster Used: N/A
Poster Load Failed: ${localUrl}
`);
                    drawerBg.style.backgroundImage = `url('${fallbackUrl}')`;
                    console.log(`[DEBUG] Drawer Poster Load Success:
Movie Title: ${title}
TMDB Poster URL: ${tmdbUrl}
Local Poster Found: No
Fallback Poster Used: Yes (${fallbackUrl})
Poster Loaded Successfully: ${fallbackUrl}
`);
                };
            } else if (initialStage === "local") {
                drawerBg.style.backgroundImage = `url('${fallbackUrl}')`;
                console.log(`[DEBUG] Drawer Poster Load Success:
Movie Title: ${title}
TMDB Poster URL: None
Local Poster Found: No
Fallback Poster Used: Yes (${fallbackUrl})
Poster Loaded Successfully: ${fallbackUrl}
`);
            }
        };
    }

    const currentMood =
        document.querySelector('input[name="mood"]:checked')?.value || "happy";
    document.getElementById("drawerWatchBtn").onclick = () => {
        markWatched(movie.id, movie.title, currentMood);
        closeMovieDrawer();
    };

    // Trailer button handler
    const trailerBtn = document.getElementById("drawerTrailerBtn");
    if (trailerBtn) {
        if (movie.trailer_url) {
            trailerBtn.disabled = false;
            trailerBtn.onclick = () => openTrailerModal(movie.title, movie.trailer_url);
        } else {
            trailerBtn.disabled = true;
            trailerBtn.title = "Trailer not available";
        }
    }

    drawer.classList.add("open");
    document.body.style.overflow = "hidden";
}

function closeMovieDrawer() {
    const drawer = document.getElementById("movieDrawer");
    if (drawer) {
        drawer.classList.remove("open");
        document.body.style.overflow = "";
    }
}

/* ── Trailer Modal ─────────────────────────────────────────────────────────── */
function openTrailerModal(movieTitle, trailerUrl) {
    const modal = document.getElementById("trailerModal");
    if (!modal) return;

    document.getElementById("trailerModalTitle").textContent = `${movieTitle} - Trailer`;
    
    const videoContainer = document.getElementById("trailerVideoContainer");
    if (videoContainer) {
        const videoId = extractYouTubeVideoId(trailerUrl);
        if (videoId) {
            videoContainer.innerHTML = `
                <iframe 
                    src="https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0&modestbranding=1" 
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                    allowfullscreen>
                </iframe>
            `;
        } else {
            videoContainer.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted);">
                    <p>Trailer not available. <a href="${trailerUrl}" target="_blank" style="color: var(--cyan);">Watch on YouTube</a></p>
                </div>
            `;
        }
    }

    modal.classList.add("active");
    document.body.style.overflow = "hidden";
}

function closeTrailerModal() {
    const modal = document.getElementById("trailerModal");
    if (modal) {
        modal.classList.remove("active");
        document.body.style.overflow = "";
        
        // Clear iframe to stop video playback
        const videoContainer = document.getElementById("trailerVideoContainer");
        if (videoContainer) {
            videoContainer.innerHTML = "";
        }
    }
}

function extractYouTubeVideoId(url) {
    if (!url) return null;
    
    const patterns = [
        /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/,
        /youtube\.com\/v\/([^&\n?#]+)/,
        /youtube\.com\/shorts\/([^&\n?#]+)/
    ];
    
    for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match && match[1]) {
            return match[1];
        }
    }
    
    return null;
}

/* ── Watch history ─────────────────────────────────────────────────────────── */
async function markWatched(movieId, title, mood) {
    try {
        const response = await fetch("/api/watch", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ movie_id: movieId, mood }),
        });
        const data = await response.json();
        if (data.success) {
            showToast("Watched!", `"${title}" added to your history.`, "📺");
            loadWatchHistory();
        } else {
            showToast("Notice", data.error || "Action failed.", "ℹ️");
        }
    } catch (error) {
        console.error(error);
        showToast("Error", "Could not update watch history.", "❌");
    }
}

async function loadWatchHistory() {
    const grid = document.getElementById("historyGrid");
    if (!grid) return;

    try {
        const response = await fetch("/api/history");
        const data = await response.json();

        if (data.success && data.history?.length > 0) {
            grid.innerHTML = "";
            data.history.forEach((item, index) => grid.appendChild(createHistoryCard(item, index)));
            
            // Show Welcome Back section!
            const welcomeSec = document.getElementById("welcomeBackSection");
            if (welcomeSec) welcomeSec.style.display = "block";
            
            // Fetch and render personalized recommendations!
            fetchPersonalizedRecommendations();
        } else {
            grid.innerHTML = `
                <div class="no-history-placeholder">
                    <p>📺 You haven't watched any movies yet. Mark a film as watched to build your taste profile.</p>
                </div>`;
        }
    } catch (error) {
        console.error("Error loading watch history:", error);
    }
}

function createHistoryCard(item, index = 99) {
    const card = document.createElement("div");
    card.className = "history-card";

    let watchedDate = "Recently";
    if (item.watched_at) {
        try {
            watchedDate = new Date(item.watched_at).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
            });
        } catch (_) {}
    }

    const tmdbPoster = item.omdb_poster || item.poster;
    const hasTmdb = tmdbPoster && tmdbPoster !== "N/A" && tmdbPoster !== "null" && tmdbPoster !== "undefined" && tmdbPoster.trim() !== "";
    const tmdbUrl = hasTmdb ? (tmdbPoster.startsWith("/") ? `https://image.tmdb.org/t/p/w500${tmdbPoster}` : tmdbPoster) : "";
    const localUrl = getLocalPosterUrl(item.title);
    const initialStage = hasTmdb ? "tmdb" : "local";
    const initialSrc = hasTmdb ? tmdbUrl : localUrl;

    const loadingAttr = index < 4 ? "eager" : "lazy";
    const safeTitle = escapeHtml(item.title);

    card.innerHTML = `
        <div class="history-poster-wrap skeleton">
            <img src="${initialSrc}" alt="${safeTitle} poster" loading="${loadingAttr}" decoding="async" 
                 data-title="${safeTitle}"
                 data-tmdb="${tmdbUrl || 'None'}"
                 data-local="${localUrl}"
                 data-fallback="/posters/default-poster.jpg"
                 data-stage="${initialStage}"
                 data-size="150x225"
                 onload="handlePosterLoad(this)"
                 onerror="handlePosterError(this)">
        </div>
        <div class="history-info">
            <h4>${escapeHtml(item.title)}</h4>
            <div class="history-meta"><span>Watched: ${watchedDate}</span></div>
            <div class="rating-interaction-block">
                <p>Your Rating</p>
                <div class="rating-stars-interactive" data-history-id="${item.history_id}">
                    ${[1, 2, 3, 4, 5].map((n) => `<span class="star" data-value="${n}">★</span>`).join("")}
                </div>
            </div>
        </div>
    `;

    const stars = card.querySelectorAll(".star");
    highlightStars(stars, item.rating_given || 0);
    stars.forEach((star) => {
        star.addEventListener("click", async () => {
            await submitMovieRating(
                item.history_id,
                parseInt(star.dataset.value, 10),
                stars
            );
        });
    });

    return card;
}

function highlightStars(stars, ratingValue) {
    stars.forEach((s) => {
        s.classList.toggle("active", parseInt(s.dataset.value, 10) <= ratingValue);
    });
}

async function submitMovieRating(historyId, rating, stars) {
    try {
        const response = await fetch("/api/rate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ history_id: historyId, rating }),
        });
        const data = await response.json();
        if (data.success) {
            highlightStars(stars, rating);
            showToast("Rated!", `You gave this film ${rating} stars.`, "⭐");
        } else {
            showToast("Error", data.error || "Failed to update rating.", "❌");
        }
    } catch (error) {
        console.error(error);
        showToast("Error", "Could not submit rating.", "❌");
    }
}

/* ── Chatbot functionality is consolidated and managed inside moumi.js ── */

/* ── Cinematic visual atmosphere background canvas & 3D tilt interaction ── */
function initCinematicBackground() {
    const container = document.querySelector('.cinematic-background');
    const canvas = document.getElementById('cinematicCanvas');
    if (!container || !canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    let width = canvas.width = window.innerWidth;
    let height = canvas.height = window.innerHeight;
    
    window.addEventListener('resize', () => {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    });
    
    // Mouse coords tracking for parallax
    let mouseX = width / 2;
    let mouseY = height / 2;
    let targetMouseX = width / 2;
    let targetMouseY = height / 2;
    
    window.addEventListener('mousemove', (e) => {
        targetMouseX = e.clientX;
        targetMouseY = e.clientY;
    });
    
    // 1. Particle class (glowing projector dust particles)
    class Particle {
        constructor() {
            this.reset();
            this.y = Math.random() * height;
        }
        reset() {
            this.x = Math.random() * width;
            this.y = height + 10;
            this.size = Math.random() * 1.5 + 0.5;
            this.speedY = -(Math.random() * 0.4 + 0.1);
            this.speedX = Math.random() * 0.2 - 0.1;
            this.alpha = Math.random() * 0.4 + 0.15;
            this.swingSpeed = Math.random() * 0.01 + 0.005;
            this.swingAmount = Math.random() * 1.2 + 0.3;
            this.angle = Math.random() * Math.PI * 2;
        }
        update(dt) {
            this.y += this.speedY * dt;
            this.angle += this.swingSpeed * dt;
            this.x += (this.speedX + Math.sin(this.angle) * this.swingAmount * 0.2) * dt;
            if (this.y < -10 || this.x < -10 || this.x > width + 10) {
                this.reset();
            }
        }
        draw() {
            ctx.save();
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(0, 212, 255, ${this.alpha})`;
            ctx.shadowColor = 'rgba(0, 212, 255, 0.45)';
            ctx.shadowBlur = this.size * 3.5;
            ctx.fill();
            ctx.restore();
        }
    }
    
    // 2. Star class (deep twinkling background stars)
    class Star {
        constructor() {
            this.x = Math.random() * width;
            this.y = Math.random() * height;
            this.size = Math.random() * 1.2 + 0.4;
            this.depth = Math.random() * 0.6 + 0.2;
            this.alpha = Math.random() * 0.6 + 0.2;
            this.twinkleSpeed = Math.random() * 0.015 + 0.005;
            this.twinkleDir = Math.random() > 0.5 ? 1 : -1;
        }
        update(dt) {
            this.alpha += this.twinkleSpeed * this.twinkleDir * dt;
            if (this.alpha > 0.85) {
                this.alpha = 0.85;
                this.twinkleDir = -1;
            } else if (this.alpha < 0.1) {
                this.alpha = 0.1;
                this.twinkleDir = 1;
            }
        }
        draw(offsetX, offsetY) {
            const drawX = (this.x + offsetX * this.depth + width) % width;
            const drawY = (this.y + offsetY * this.depth + height) % height;
            ctx.beginPath();
            ctx.arc(drawX, drawY, this.size, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255, 255, 255, ${this.alpha})`;
            ctx.fill();
        }
    }
    
    // 3. ShootingStar class (occasional streaks with trail)
    class ShootingStar {
        constructor() {
            this.reset();
            this.active = false;
        }
        reset() {
            this.x = Math.random() * (width * 0.6);
            this.y = Math.random() * (height * 0.4);
            this.length = Math.random() * 60 + 30;
            this.speedX = Math.random() * 6 + 4;
            this.speedY = Math.random() * 2 + 1.2;
            this.opacity = 1.0;
            this.active = false;
            this.delay = Math.random() * 450 + 150;
        }
        update(dt) {
            if (!this.active) {
                this.delay -= dt;
                if (this.delay <= 0) {
                    this.active = true;
                }
                return;
            }
            this.x += this.speedX * dt;
            this.y += this.speedY * dt;
            this.opacity -= 0.015 * dt;
            if (this.opacity <= 0 || this.x > width || this.y > height) {
                this.reset();
            }
        }
        draw() {
            if (!this.active) return;
            ctx.save();
            ctx.beginPath();
            const grad = ctx.createLinearGradient(this.x, this.y, this.x - this.speedX * 4, this.y - this.speedY * 4);
            grad.addColorStop(0, `rgba(255, 255, 255, ${this.opacity * 0.85})`);
            grad.addColorStop(1, 'rgba(0, 212, 255, 0)');
            ctx.strokeStyle = grad;
            ctx.lineWidth = 1.2;
            ctx.moveTo(this.x, this.y);
            ctx.lineTo(this.x - this.speedX * 4, this.y - this.speedY * 4);
            ctx.stroke();
            ctx.restore();
        }
    }

    // 4. FogParticle class (drifting atmospheric cinematic fog)
    class FogParticle {
        constructor() {
            this.reset();
            this.x = Math.random() * width;
        }
        reset() {
            this.x = -300;
            this.y = Math.random() * height;
            this.size = Math.random() * 200 + 150;
            this.speedX = Math.random() * 0.15 + 0.05;
            this.alpha = Math.random() * 0.025 + 0.008;
            this.depth = Math.random() * 0.4 + 0.1;
        }
        update(dt) {
            this.x += this.speedX * dt;
            if (this.x > width + 300) {
                this.reset();
            }
        }
        draw(offsetX, offsetY) {
            ctx.save();
            ctx.globalCompositeOperation = 'screen';
            const drawX = this.x + offsetX * this.depth;
            const drawY = this.y + offsetY * this.depth;
            const grad = ctx.createRadialGradient(drawX, drawY, 0, drawX, drawY, this.size);
            grad.addColorStop(0, `rgba(0, 212, 255, ${this.alpha})`);
            grad.addColorStop(0.5, `rgba(0, 120, 220, ${this.alpha * 0.4})`);
            grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.arc(drawX, drawY, this.size, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        }
    }
    
    // Initialize pools
    const particles = [];
    for (let i = 0; i < 40; i++) particles.push(new Particle());
    
    const stars = [];
    for (let i = 0; i < 90; i++) stars.push(new Star());
    
    const shootingStars = [new ShootingStar(), new ShootingStar()];

    const fogs = [];
    for (let i = 0; i < 8; i++) fogs.push(new FogParticle());
    
    let time = 0;
    let lastFrameTime = performance.now();
    
    // Render loop
    function render(now) {
        const dt = Math.min(3.0, (now - lastFrameTime) / 16.666); // scale by elapsed time compared to 60fps
        lastFrameTime = now;

        mouseX += (targetMouseX - mouseX) * 0.045 * dt;
        mouseY += (targetMouseY - mouseY) * 0.045 * dt;
        
        const offsetX = (width / 2 - mouseX) * 0.025;
        const offsetY = (height / 2 - mouseY) * 0.025;
        
        time += 0.00065 * dt;
        
        ctx.clearRect(0, 0, width, height);
        
        // Draw Layer 1: Stars with parallax
        for (let star of stars) {
            star.update(dt);
            star.draw(offsetX, offsetY);
        }
        
        for (let ss of shootingStars) {
            ss.update(dt);
            ss.draw();
        }
        
        // Draw Layer 2: Aurora waves (subtle blend)
        ctx.save();
        ctx.globalCompositeOperation = 'screen';
        
        // Wave 1 - Cyan glow
        ctx.beginPath();
        const baseOffset1 = height * 0.22 + Math.sin(time * 1.8) * 32;
        ctx.moveTo(0, baseOffset1);
        for (let x = 0; x <= width; x += 30) {
            const y = baseOffset1 + Math.sin(x * 0.0035 + time * 2.5) * 35 + Math.cos(x * 0.0015 + time * 1.5) * 18;
            ctx.lineTo(x, y);
        }
        ctx.lineTo(width, height);
        ctx.lineTo(0, height);
        ctx.closePath();
        
        const auroraGrad1 = ctx.createLinearGradient(0, height * 0.15, 0, height * 0.7);
        auroraGrad1.addColorStop(0, 'rgba(0, 212, 255, 0.04)');
        auroraGrad1.addColorStop(0.5, 'rgba(0, 120, 220, 0.015)');
        auroraGrad1.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.fillStyle = auroraGrad1;
        ctx.fill();
        
        // Wave 2 - Purple glow
        ctx.beginPath();
        const baseOffset2 = height * 0.26 + Math.cos(time * 1.4) * 24;
        ctx.moveTo(0, baseOffset2);
        for (let x = 0; x <= width; x += 30) {
            const y = baseOffset2 + Math.sin(x * 0.0028 - time * 2.0) * 30 + Math.cos(x * 0.0042 + time * 1.2) * 15;
            ctx.lineTo(x, y);
        }
        ctx.lineTo(width, height);
        ctx.lineTo(0, height);
        ctx.closePath();
        
        const auroraGrad2 = ctx.createLinearGradient(0, height * 0.15, 0, height * 0.75);
        auroraGrad2.addColorStop(0, 'rgba(140, 0, 255, 0.025)');
        auroraGrad2.addColorStop(0.5, 'rgba(60, 0, 180, 0.008)');
        auroraGrad2.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.fillStyle = auroraGrad2;
        ctx.fill();
        
        ctx.restore();
        
        // Draw Layer 3: Drifting fog
        for (let fog of fogs) {
            fog.update(dt);
            fog.draw(offsetX, offsetY);
        }

        // Draw Layer 4: Projector Beam
        ctx.save();
        ctx.globalCompositeOperation = 'screen';
        
        const beamX = width * 0.5;
        const beamY = -50;
        const targetBeamX = width * 0.5 + (mouseX - width * 0.5) * 0.12;
        
        const projectorGrad = ctx.createRadialGradient(beamX, beamY, 0, beamX, beamY, height * 0.9);
        projectorGrad.addColorStop(0, 'rgba(0, 212, 255, 0.055)');
        projectorGrad.addColorStop(0.3, 'rgba(0, 150, 255, 0.022)');
        projectorGrad.addColorStop(0.7, 'rgba(0, 60, 180, 0.005)');
        projectorGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
        
        ctx.beginPath();
        ctx.moveTo(beamX - 10, beamY);
        ctx.lineTo(targetBeamX - width * 0.28, height);
        ctx.lineTo(targetBeamX + width * 0.28, height);
        ctx.lineTo(beamX + 10, beamY);
        ctx.closePath();
        ctx.fillStyle = projectorGrad;
        ctx.fill();
        
        ctx.restore();
        
        // Draw Layer 5: Tiny floating particles
        for (let p of particles) {
            p.update(dt);
            p.draw();
        }
        
        if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            requestAnimationFrame(render);
        } else {
            ctx.clearRect(0, 0, width, height);
            ctx.fillStyle = 'rgba(0, 212, 255, 0.015)';
            ctx.fillRect(0, 0, width, height);
        }
    }
    
    requestAnimationFrame(render);
}

function initMovieCardTilt() {
    // Respect prefers-reduced-motion configuration
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    document.addEventListener('mousemove', (e) => {
        const card = e.target.closest('.movie-card');
        if (!card) return;
        
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        
        // Limit max rotation to keep it subtle and elegant
        const maxRotateX = 6;
        const maxRotateY = 6;
        
        const rotateX = ((centerY - y) / centerY) * maxRotateX;
        const rotateY = ((x - centerX) / centerX) * maxRotateY;
        
        requestAnimationFrame(() => {
            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.025, 1.025, 1.025)`;
            card.style.transition = 'none';
            card.style.boxShadow = '0 16px 48px rgba(0, 212, 255, 0.25), 0 0 32px rgba(0, 212, 255, 0.15)';
        });
    });
    
    document.addEventListener('mouseout', (e) => {
        const card = e.target.closest('.movie-card');
        if (!card) return;
        
        requestAnimationFrame(() => {
            card.style.transform = '';
            card.style.transition = 'transform 0.5s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.35s ease, border-color 0.35s ease';
            card.style.boxShadow = '';
        });
    });
}

/* ── AI taste profile tracking & upgrades ────────────────────────────────── */
function logMovieClick(movieId) {
    if (!movieId) return;
    fetch("/api/click", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ movie_id: movieId })
    }).catch(err => console.error("Error logging movie click:", err));
}

async function fetchPersonalizedRecommendations() {
    const grid = document.getElementById("personalizedGrid");
    const section = document.getElementById("personalizedRecommendations");
    const divider = document.querySelector(".recommended-divider");
    if (!grid || !section) return;

    try {
        const response = await fetch("/api/recommendations-personalized");
        const data = await response.json();

        if (data.success && data.movies?.length > 0) {
            grid.innerHTML = "";
            data.movies.forEach((movie, index) => {
                const card = createPersonalizedMovieCard(movie, index);
                grid.appendChild(card);
                requestAnimationFrame(() => card.classList.add("visible"));
            });
            console.log(`[DEBUG] Movies rendered: ${data.movies.length} (personalized)`);
            section.style.display = "block";
            if (divider) divider.style.display = "block";
            initMovieCardTilt();
        } else {
            section.style.display = "none";
            if (divider) divider.style.display = "none";
        }
    } catch (error) {
        console.error("Error loading personalized recommendations:", error);
    }
}

function createPersonalizedMovieCard(movie, index = 99) {
    const card = document.createElement("article");
    card.className = "movie-card";

    const tmdbPoster = movie.omdb_poster || movie.poster;
    const hasTmdb = tmdbPoster && tmdbPoster !== "N/A" && tmdbPoster !== "null" && tmdbPoster !== "undefined" && tmdbPoster.trim() !== "";
    const tmdbUrl = hasTmdb ? (tmdbPoster.startsWith("/") ? `https://image.tmdb.org/t/p/w500${tmdbPoster}` : tmdbPoster) : "";
    const localUrl = getLocalPosterUrl(movie.title);
    const initialStage = hasTmdb ? "tmdb" : "local";
    const initialSrc = hasTmdb ? tmdbUrl : localUrl;
    
    const loadingAttr = index < 4 ? "eager" : "lazy";
    const safeTitle = escapeHtml(movie.title);

    const displayRating = movie.imdb_rating && movie.imdb_rating !== "N/A" ? movie.imdb_rating : movie.rating;
    const langClass = (movie.language || "default").toLowerCase().replace(/\s+/g, "-");

    card.innerHTML = `
        <div class="movie-poster-container skeleton">
            <img src="${initialSrc}" alt="${safeTitle} poster" loading="${loadingAttr}" decoding="async" 
                 data-title="${safeTitle}"
                 data-tmdb="${tmdbUrl || 'None'}"
                 data-local="${localUrl}"
                 data-fallback="/posters/default-poster.jpg"
                 data-stage="${initialStage}"
                 data-size="300x450"
                 onload="handlePosterLoad(this)"
                 onerror="handlePosterError(this)">
            <span class="lang-badge lang-${langClass}">${escapeHtml(movie.language || "—")}</span>
        </div>
        <div class="movie-info-body">
            <div class="rec-reason-badge">💡 ${escapeHtml(movie.reason)}</div>
            <div class="movie-card-badges">
                <span class="genre-badge">${escapeHtml(movie.genre || "")}</span>
            </div>
            <div class="movie-card-meta">
                <span>⭐ IMDb: ${displayRating}</span>
                <span>🕐 ${movie.runtime} min</span>
            </div>
            <h3>${safeTitle}</h3>
            <p class="movie-card-plot">${escapeHtml(truncateText(movie.omdb_plot || "Plot unavailable.", 120))}</p>
            <div class="movie-card-actions">
                <a class="card-action-btn primary" href="${movie.trailer_url || 'https://www.youtube.com/results?search_query=' + encodeURIComponent(movie.title + ' trailer')}" target="_blank" rel="noopener">▶ Trailer</a>
                <button type="button" class="card-action-btn" data-watchlist="${escapeHtml(movie.title)}">＋ Watchlist</button>
                <button type="button" class="card-action-btn ghost" data-info='${escapeAttr(JSON.stringify(movie))}'>Info</button>
                <button type="button" class="card-action-btn" data-watch-id="${movie.id}" data-watch-title="${escapeHtml(movie.title)}">Watch</button>
            </div>
        </div>
    `;

    card.querySelector("[data-info]")?.addEventListener("click", (e) => {
        const mv = JSON.parse(e.currentTarget.dataset.info);
        logMovieClick(mv.id);
        openMovieDrawer(mv);
    });
    card.querySelector("[data-watchlist]")?.addEventListener("click", (e) => {
        toggleWatchlist(e.currentTarget.dataset.watchlist);
    });
    card.querySelector("[data-watch-id]")?.addEventListener("click", (e) => {
        markWatched(String(e.currentTarget.dataset.watchId), e.currentTarget.dataset.watchTitle, "happy");
        closeMovieDrawer();
    });

    return card;
}

/* ── Trending Movies section ─────────────────────────────────────────────── */
function initTrendingMovies() {
    const tabToday = document.getElementById("tabTrendingToday");
    const tabWeek = document.getElementById("tabTrendingWeek");
    if (!tabToday || !tabWeek) return;

    tabToday.addEventListener("click", () => {
        tabToday.classList.add("active");
        tabWeek.classList.remove("active");
        fetchTrending("day");
    });

    tabWeek.addEventListener("click", () => {
        tabWeek.classList.add("active");
        tabToday.classList.remove("active");
        fetchTrending("week");
    });

    fetchTrending("day");
}

async function fetchTrending(timeWindow) {
    const grid = document.getElementById("trendingGrid");
    if (!grid) return;

    grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">Loading trending movies...</div>`;

    try {
        const response = await fetch(`/api/trending?time_window=${timeWindow}`);
        const data = await response.json();

        if (data.success && data.movies?.length > 0) {
            grid.innerHTML = "";
            data.movies.forEach((movie, index) => {
                const card = createTrendingMovieCard(movie, index);
                grid.appendChild(card);
                requestAnimationFrame(() => card.classList.add("visible"));
            });
            console.log(`[DEBUG] Movies rendered: ${data.movies.length} (trending)`);
            initMovieCardTilt();
        } else {
            grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">No trending movies found.</div>`;
        }
    } catch (error) {
        console.error("Error loading trending movies:", error);
        grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--danger);">Error loading trending movies.</div>`;
    }
}

function createTrendingMovieCard(movie, index = 99) {
    const card = document.createElement("article");
    card.className = "movie-card";

    const tmdbPoster = movie.omdb_poster || movie.poster;
    const hasTmdb = tmdbPoster && tmdbPoster !== "N/A" && tmdbPoster !== "null" && tmdbPoster !== "undefined" && tmdbPoster.trim() !== "";
    const tmdbUrl = hasTmdb ? (tmdbPoster.startsWith("/") ? `https://image.tmdb.org/t/p/w500${tmdbPoster}` : tmdbPoster) : "";
    const localUrl = getLocalPosterUrl(movie.title);
    const initialStage = hasTmdb ? "tmdb" : "local";
    const initialSrc = hasTmdb ? tmdbUrl : localUrl;
    
    const loadingAttr = index < 4 ? "eager" : "lazy";
    const safeTitle = escapeHtml(movie.title);

    const displayRating = movie.rating || 0.0;
    const langClass = (movie.language || "default").toLowerCase().replace(/\s+/g, "-");
    
    const popularityDisplay = movie.popularity ? `<span class="ml-match-score">🔥 Pop: ${Math.round(movie.popularity)}</span>` : '';

    card.innerHTML = `
        <div class="movie-poster-container skeleton">
            <img src="${initialSrc}" alt="${safeTitle} poster" loading="${loadingAttr}" decoding="async" 
                 data-title="${safeTitle}"
                 data-tmdb="${tmdbUrl || 'None'}"
                 data-local="${localUrl}"
                 data-fallback="/posters/default-poster.jpg"
                 data-stage="${initialStage}"
                 data-size="300x450"
                 onload="handlePosterLoad(this)"
                 onerror="handlePosterError(this)">
            <span class="lang-badge lang-${langClass}">${escapeHtml(movie.language || "—")}</span>
        </div>
        <div class="movie-info-body">
            <div class="movie-card-badges">
                <span class="genre-badge">${escapeHtml(movie.genre || "")}</span>
                ${popularityDisplay}
            </div>
            <div class="movie-card-meta">
                <span>⭐ Rating: ${displayRating}</span>
                <span>📅 ${movie.release_date || "N/A"}</span>
            </div>
            <h3>${safeTitle}</h3>
            <p class="movie-card-plot">${escapeHtml(truncateText(movie.overview || "Plot unavailable.", 120))}</p>
            <div class="movie-card-actions">
                <button type="button" class="card-action-btn" data-watchlist="${escapeHtml(movie.title)}">＋ Watchlist</button>
                <button type="button" class="card-action-btn ghost" data-info='${escapeAttr(JSON.stringify(movie))}'>Info</button>
            </div>
        </div>
    `;

    card.querySelector("[data-info]")?.addEventListener("click", (e) => {
        const m = JSON.parse(e.currentTarget.dataset.info);
        const details = {
            id: m.id,
            title: m.title,
            omdb_poster: m.poster,
            omdb_plot: m.overview,
            omdb_year: m.release_date,
            runtime: 120,
            rating: m.rating,
            imdb_rating: m.rating,
            genre: m.genre,
            language: m.language,
            omdb_director: "N/A",
            omdb_cast: "N/A",
            trailer_url: ""
        };
        logMovieClick(m.id);
        openMovieDrawer(details);
    });
    card.querySelector("[data-watchlist]")?.addEventListener("click", (e) => {
        toggleWatchlist(e.currentTarget.dataset.watchlist);
    });

    return card;
}

function initWelcomeBackSection() {
    const welcomeSec = document.getElementById("welcomeBackSection");
    if (!welcomeSec) return;

    if (!PAGE.userId) {
        welcomeSec.style.display = "none";
        return;
    }

    console.log(`[DEBUG] User detected: ID = ${PAGE.userId}`);

    let name = PAGE.userName || localStorage.getItem("userName") || localStorage.getItem("username");
    if (!name) {
        const navNameEl = document.querySelector(".nav-links strong") || document.querySelector(".nav-profile strong");
        if (navNameEl) {
            name = navNameEl.textContent.trim();
        }
    }
    
    if (name) {
        name = name.trim();
        if (name === "None" || name === "null" || name === "undefined" || name === "You") {
            name = "";
        }
    }

    console.log(`[DEBUG] Username detected: "${name || 'Movie Lover'}"`);

    const welcomeUserNameSpan = document.getElementById("welcomeUserName");
    const welcomeHeading = welcomeSec.querySelector(".welcome-back-card h2");

    if (name) {
        if (welcomeUserNameSpan) {
            welcomeUserNameSpan.textContent = name;
        } else if (welcomeHeading) {
            welcomeHeading.innerHTML = `Hey <span class="text-cyan">${escapeHtml(name)}</span> 👋`;
        }
    } else {
        if (welcomeHeading) {
            welcomeHeading.innerHTML = `Hey <span class="text-cyan">Movie Lover</span> 👋`;
        }
    }

    welcomeSec.style.display = "block";
    welcomeSec.classList.add("fade-in-animated");
    console.log("[DEBUG] Welcome section rendered");
}

