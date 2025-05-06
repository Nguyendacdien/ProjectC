// Get number of each field
var i = $('.instructionClass').length;
var x = $('.allergenClass').length;
var y = $('.ingredientClass').length;

// Hiển thị nút xóa nếu cần
if (i > 1) $("#ins-remove").css("display", "inline-block");
if (x > 0) $("#allerg-remove").css("display", "inline-block");
if (y > 1) $("#ing-remove").css("display", "inline-block");

function add_more_instructions() {
    i++;
    $(".instructions").append(`
        <br>
        <div id="ins${i}" class="col-md-6 mb-3">
            <label>Step ${i}:</label>
            <input name="instruction${i}" type="text" class="form-control instructionClass" placeholder="Please Enter The Instructions One At A Time" autocomplete="off" />
        </div>
    `);
    if (i > 1) $("#ins-remove").css("display", "inline-block");
}

function remove_instructions() {
    $("#ins" + i).remove();
    i--;
    if (i < 2) $("#ins-remove").css("display", "none");
}

function add_more_allergens() {
    x++;
    $(".allergens").append(`
        <div id="allerg${x}" class="col-md-6 mb-3">
            <label>Allergen ${x}:</label>
            <input name="allergen${x}" type="text" class="form-control allergenClass" placeholder="Please Enter Any Allergens One At A Time" autocomplete="off" />
        </div>
    `);
    if (x > 0) $("#allerg-remove").css("display", "inline-block");
}

function remove_allergens() {
    $("#allerg" + x).remove();
    x--;
    if (x === 0) $("#allerg-remove").css("display", "none");
}

function add_more_ingredients() {
    y++;
    $(".ingredients").append(`
        <br>
        <div id="ing${y}" class="col-md-6 mb-3">
            <label>Ingredient ${y}:</label>
            <input name="ingredient${y}" type="text" class="form-control ingredientClass" placeholder="Please Enter Any Ingredients One At A Time" autocomplete="off" />
        </div>
    `);
    if (y > 1) $("#ing-remove").css("display", "inline-block");
}

function remove_ingredients() {
    $("#ing" + y).remove();
    y--;
    if (y < 2) $("#ing-remove").css("display", "none");
}
document.querySelector("form.needs-validation").addEventListener("submit", function (e) {
    let valid = true;

    // Kiểm tra instructions
    document.querySelectorAll(".instructionClass").forEach((el) => {
        if (el.value.trim() === "") {
            el.classList.add("is-invalid");
            valid = false;
        } else {
            el.classList.remove("is-invalid");
        }
    });

    // Kiểm tra ingredients
    document.querySelectorAll(".ingredientClass").forEach((el) => {
        if (el.value.trim() === "") {
            el.classList.add("is-invalid");
            valid = false;
        } else {
            el.classList.remove("is-invalid");
        }
    });

    // Kiểm tra allergens
    document.querySelectorAll(".allergenClass").forEach((el) => {
        if (el.value.trim() === "") {
            el.classList.add("is-invalid");
            valid = false;
        } else {
            el.classList.remove("is-invalid");
        }
    });

    if (!valid) {
        e.preventDefault(); // Ngăn không cho submit nếu có input trống
        alert("Please fill in all added fields before submitting.");
    }
});