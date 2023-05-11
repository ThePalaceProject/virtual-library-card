$(document).ready(function() {
    if (!$){
        // Since Django Admin imports jquery.init.js that removes $ from the scope we need to define $ again.
        $ = django.jQuery;
    }
    // When place name is selected we automatically fill in place type and parent.
    $('#id_name').on('select2:select', function(e) {
        // Triggers when the place name dropdown is selected.

        // Data is selected item from place name dropdown with all the attributes sent by the backend.
        // data = {
        //     "id": "<id>",
        //     "name": "<name>",
        //     "text": "<descriptive name>",
        //     "type": "<type>",
        //     "parents": [ - list of parents sorted by proximity in hierarchy
        //         {"type": "<parent_type>", "value": "<parent_name>"},
        //         ...
        //     ]"
        // }
        var data = e.params.data;

        // Set place type.
        $("#id_type").val(data.type).change();

        // Set parent.
        var parent_options = $("#id_parent option");
        var place_parents = $(data.parents);

        // For each place parent received from the API we iterate through the available parents in the parent dropdown.
        // When we match the first parent we stop looping. Backend API is returning parents in proximity order
        // so by stopping on the first parent we find we will chose the nearest parent.
        var parent_found = false;
        place_parents.each(function(index, parent) {
            parent_options.each(function(index, option) {
                var option_element = $(option);

                if (option_element.text().includes(parent.type) && option_element.text().includes(parent.value)) {
                    $("#id_parent").val(option_element.val()).change();
                    parent_found = true;

                    return false // Breaks the inner each loop.
                }
            })

            if (parent_found === true) {
                return false // Breaks the outer each loop.
            }
        })

        if (parent_found === false) {
            // If you are editing existing place and we haven't found the parent we clear out the parent dropdown
            // so the wrong parent wouldn't be accidentally saved.
            $("#id_parent").val('');
        }
    });

    // To make select2 ids unique for the place name dropdown we are using place name + '|' + API id. Form sends the
    // option id to the backend so before submitting the form we need to make sure we are using only the place name,
    // without the suffix "|id" part.
    $("#place_form").on("submit", function(event) {
        var name_select = $("#id_name");
        var selected_name_items = name_select.select2("data");

        // If someone is saving form that is not filled out completely.
        if (selected_name_items.length === 0) {
            return
        }

        var selected_name_item = selected_name_items[0];

        var real_place_name = selected_name_item.name;

        if (real_place_name == null) {
            // User is creating place with name not found in the API so we don't do anything to it.
            return;
        }

        // To be able to use real_place_name as a value that is actually selected and sent to the backend we need to
        // create a new option with real_place_name as a value.
        var cleaned_option = new Option(selected_name_item.text, real_place_name, false, false);
        name_select.append(cleaned_option);
        name_select.val(real_place_name);
    })
});
