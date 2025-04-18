document.addEventListener("DOMContentLoaded", () => {
    // Add fade-in animation to each section on page load
    const sections = document.querySelectorAll("section");
    sections.forEach((sec, index) => {
        setTimeout(() => {
            sec.classList.add("fade-in");
        }, index * 200); // Staggered animation effect
    });

   
    
});
