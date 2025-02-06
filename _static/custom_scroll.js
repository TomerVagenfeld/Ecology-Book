window.addEventListener("DOMContentLoaded", () => {
    console.log("Custom search script loaded.");

    // Function to scroll to the first highlighted result
    const scrollToResult = () => {
        const firstResult = document.querySelector('.highlighted');
        if (firstResult) {
            firstResult.scrollIntoView({ behavior: 'smooth', block: 'center' });
            console.log("Scrolled to the first highlighted result.");
            return true; // Scrolling succeeded
        } else {
            console.log("No highlighted result found yet.");
            return false; // No result to scroll to
        }
    };

    // Periodically check for highlighted elements
    const checkForHighlight = setInterval(() => {
        console.log("Checking for highlighted results...");
        const scrolled = scrollToResult();
        if (scrolled) {
            clearInterval(checkForHighlight); // Stop checking after scrolling
            console.log("Stopped checking after successful scroll.");
        }
    }, 300); // Check every 300ms
});
