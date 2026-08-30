import re

with open('public/introduce.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Add ID and adjust padding/smooth scroll on the carousel container
target1 = '''        <div class="carousel-container relative w-full">
            <div class="flex gap-8 overflow-x-auto snap-x snap-mandatory px-6 md:px-12 xl:px-[calc((100vw-85rem)/2)] pb-16 pt-4 hide-scrollbar"
                style="scroll-padding-left: 2rem;">'''
replacement1 = '''        <div class="carousel-container relative w-full group/carousel">
            <div id="cardCarousel" class="flex gap-8 overflow-x-auto snap-x snap-mandatory px-6 md:px-12 xl:px-[calc((100vw-85rem)/2)] pb-24 pt-4 hide-scrollbar scroll-smooth"
                style="scroll-padding-left: 2rem;">'''
html = html.replace(target1, replacement1)

# Add the buttons right after the cards (before the closing div of carousel-container)
target2 = '''                    </div>
                </div>

            </div>
        </div>'''
replacement2 = '''                    </div>
                </div>

            </div>
            
            <!-- Navigation Buttons -->
            <div class="absolute bottom-6 right-6 md:right-12 xl:right-[calc((100vw-85rem)/2)] flex gap-4">
                <button id="carouselPrevBtn" class="w-12 h-12 rounded-full bg-gray-200/50 hover:bg-gray-300/80 backdrop-blur-md flex items-center justify-center text-gray-700 transition-colors shadow-sm cursor-pointer">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>
                </button>
                <button id="carouselNextBtn" class="w-12 h-12 rounded-full bg-gray-200/50 hover:bg-gray-300/80 backdrop-blur-md flex items-center justify-center text-gray-700 transition-colors shadow-sm cursor-pointer">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></svg>
                </button>
            </div>
        </div>'''
html = html.replace(target2, replacement2)

# Add the JavaScript at the end
js_to_add = '''
        // Carousel Navigation
        const cardCarousel = document.getElementById('cardCarousel');
        const prevBtn = document.getElementById('carouselPrevBtn');
        const nextBtn = document.getElementById('carouselNextBtn');

        if (cardCarousel && prevBtn && nextBtn) {
            const scrollAmount = window.innerWidth > 768 ? 600 : 350; // approximate card width
            
            prevBtn.addEventListener('click', () => {
                cardCarousel.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
            });
            
            nextBtn.addEventListener('click', () => {
                cardCarousel.scrollBy({ left: scrollAmount, behavior: 'smooth' });
            });
        }
    </script>'''
html = html.replace('    </script>', js_to_add)

with open('public/introduce.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Done adding buttons!")
