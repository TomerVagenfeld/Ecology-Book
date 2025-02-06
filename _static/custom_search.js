window.addEventListener("DOMContentLoaded", () => {
    console.log("Custom search script loaded.");

    // Wait for the search index to load
    const checkSearchIndex = setInterval(() => {
        if (window.search && window.search._index) {
            console.log("Search index found, enhancing functionality.");

            // Sanitize the search results to remove HTML tags
            const searchResults = document.querySelectorAll('.search-results .search');
            searchResults.forEach(result => {
                result.innerHTML = result.innerHTML.replace(/<\/?[^>]+(>|$)/g, ""); // Remove HTML tags
            });

            // Clear the interval once done
            clearInterval(checkSearchIndex);
        }
    }, 100);
});
