// Hàm sắp xếp theo tên
function sort_by_name() {
    const items = Array.from(document.querySelectorAll('.recipe-link'));
    items.sort((a, b) => {
        const nameA = a.getAttribute('data-name');
        const nameB = b.getAttribute('data-name');
        return nameA.localeCompare(nameB);
    });
    const container = document.querySelector('.card-container');
    items.forEach(item => container.appendChild(item));
}

// Hàm sắp xếp theo tác giả
function sort_by_author() {
    const items = Array.from(document.querySelectorAll('.recipe-link'));
    items.sort((a, b) => {
        const authorA = a.getAttribute('data-author');
        const authorB = b.getAttribute('data-author');
        return authorA.localeCompare(authorB);
    });
    const container = document.querySelector('.card-container');
    items.forEach(item => container.appendChild(item));
}

// Hàm sắp xếp theo upvotes
function sort_by_upvotes() {
    const items = Array.from(document.querySelectorAll('.recipe-link'));
    items.sort((a, b) => {
        const upvotesA = parseInt(a.getAttribute('data-upvotes'));
        const upvotesB = parseInt(b.getAttribute('data-upvotes'));
        return upvotesB - upvotesA; // Sắp xếp giảm dần
    });
    const container = document.querySelector('.card-container');
    items.forEach(item => container.appendChild(item));
}

// Hàm sắp xếp theo downvotes
function sort_by_downvotes() {
    const items = Array.from(document.querySelectorAll('.recipe-link'));
    items.sort((a, b) => {
        const downvotesA = parseInt(a.getAttribute('data-downvotes'));
        const downvotesB = parseInt(b.getAttribute('data-downvotes'));
        return downvotesB - downvotesA; // Sắp xếp giảm dần
    });
    const container = document.querySelector('.card-container');
    items.forEach(item => container.appendChild(item));
}