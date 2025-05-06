    //Get number of each field
    var i = $('.instructionClass').length;
    var x = $('.allergenClass').length;
    var y = $('.ingredientClass').length;
    //If there is more than the relevent variable in each field show delete button
    if (i > 1) {
        $("#ins-remove").css("display", "inline-block");
    }
    if (x > 1) {
        $("#allerg-remove").css("display", "inline-block");
    }
    if (y > 1) {
        $("#ing-remove").css("display", "inline-block");
    }

    function add_more_instructions() {
        i++;
        $(".instructions").append(`
            <br>
            <div id='ins${i}' class='col-md-6 mb-3'>
                <label class="text-white">Step ${i}:</label>
                <input name='instruction2' type='text' class='form-control instructionClass' placeholder='Please Enter The Instructions One At A Time' autocomplete="off">
            </div>
        `);
    
        if (i > 1) {
            $("#ins-remove").css("display", "inline-block");
        }
    }
    

    function remove_instructions() {
        //When the delete button is pressed delete a field
        $("#ins" + i).remove();
        i--;
        if (i < 2) {
            $("#ins-remove").css("display", "none");
        }
    }

    function add_more_allergens() {
        //When the add button is pressed add a field
        x++;
        $(".allergens").append("<div id ='allerg" + x + "' class='col-md-6 mb-3'><input name='allergen2' type='text' class='form-control' placeholder='Please Enter Any Allergens One At A Time' </div>");
        if (x > 1) {
            $("#allerg-remove").css("display", "inline-block");
        }
    }

    function remove_allergens() {
        //When the delete button is pressed delete a field
        $("#allerg" + x).remove();
        x--;
        if (x < 2) {
            $("#allerg-remove").css("display", "none");
        }
    }

    function add_more_ingredients() {
        //When the add button is pressed add a field
        y++;
        $(".ingredients").append("<br><div  class='col-md-6 mb-3' id='ing" + y + "'><input name='ingredient2' type='text' class='form-control' placeholder='Please Enter Any Ingredients One At A Time' </div>");
        if (y > 1) {
            $("#ing-remove").css("display", "inline-block");
        }
    }

    function remove_ingredients() {
        //When the delete button is pressed delete a field
        $("#ing" + y).remove();
        y--;
        if (y < 2) {
            $("#ing-remove").css("display", "none");
        }
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
            e.preventDefault(); // Ngăn submit nếu có trường bị bỏ trống
            alert("Please fill in all added fields before submitting.");
        }
    });