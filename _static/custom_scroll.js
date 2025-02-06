window.addEventListener("DOMContentLoaded", () => {
    console.log("Custom search script loaded.");

    // Wait for the search functionality to initialize
    const checkSearchIndex = setInterval(() => {
        console.log("Checking for search index...");
        if (window.Search && window.Search.query) {
            console.log("Search functionality initialized.");

            // Stop the interval as the search functionality is found
            clearInterval(checkSearchIndex);

            // Scroll to the first highlighted result when results are loaded
            const scrollToResult = () => {
                const firstResult = document.querySelector('.search-results .highlighted');
                if (firstResult) {
                    firstResult.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    console.log("Scrolled to first search result.");
                } else {
                    console.warn("No highlighted result found.");
                }
            };

            // Observe changes in the search results
            const searchResultsContainer = document.querySelector('.search-results');
            if (searchResultsContainer) {
                const observer = new MutationObserver((mutationsList) => {
                    for (let mutation of mutationsList) {
                        if (mutation.type === 'childList') {
                            scrollToResult(); // Scroll when new results are added
                            observer.disconnect(); // Stop observing after scrolling
                            break;
                        }
                    }
                });

                observer.observe(searchResultsContainer, { childList: true, subtree: true });
            } else {
                console.warn("Search results container not found.");
            }
        }
    }, 100); // Check every 100ms
});
