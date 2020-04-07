
function toggle_time() {
    var future = $('#future_talks');
    var past = $('#past_talks');
    if (future.is(":visible"))
    {
        future.hide();
        past.show();
    } else {
        past.hide();
        future.show();
    }
}

/*
Old version
function toggle_filter() {
    var filt_btn = $('#topic-filter-btn');
    var filt_menu = $("#filter-menu");
    filt_btn.text("Filter");
    if (filt_menu.is(":hidden")) {
        filt_btn.html("Hide filters");
    } else {
        filt_btn.html("Show filters");
    }
    filt_menu.slideToggle(300);
    return false;
}
*/

function setCookie(name,value) {
    document.cookie = name + "=" + (value || "") + ";path=/";
}
function getCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for(var i=0;i < ca.length;i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1,c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
    }
    return null;
}
function eraseCookie(name) {
    document.cookie = name+'=; Max-Age=-99999999;';
}
const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
setCookie("browser_timezone", tz);
function addTopic(cat) {
    var cur_cats = getCookie("topics");
    if (cur_cats) {
        cur_cats = cur_cats + "," + cat;
    } else {
        cur_cats = cat;
    }
    setCookie("topics", cur_cats);
    return cur_cats;
}
function removeTopic(cat) {
    var cur_cats = getCookie("topics");
    cur_cats = cur_cats.replace(cat, "").replace(",,",",");
    if (cur_cats.startsWith(",")) cur_cats = cur_cats.slice(1);
    if (cur_cats.endsWith(",")) cur_cats = cur_cats.slice(0, -1);
    setCookie("topics", cur_cats);
    return cur_cats;
}

function topicFiltering() {
    return $('#enable_topic_filter').is(":checked");
}
function calFiltering() {
    return $('#enable_calendar_filter').is(":checked");
}

function setTopicLinks() {
    var cur_cats = getCookie("topics");
    $(".talk").addClass("topic-filtered");
    if (cur_cats == null) {
        setCookie("topics", "");
        setCookie("filter_topic", "0");
        setCookie("filter_calendar", "0");
        // Set the following in preparation so we don't need to worry about them not existing.
        setCookie("filter_location", "0");
        setCookie("filter_time", "0");
    } else {
        $('#enable_topic_filter').prop("checked", Boolean(parseInt(getCookie("filter_topic"))));
        $('#enable_calendar_filter').prop("checked", Boolean(parseInt(getCookie("filter_calendar"))));
        cur_cats = cur_cats.split(",");
        for (var i=0; i<cur_cats.length; i++) {
            $("#catlink-" + cur_cats[i]).addClass("catselected");
            $(".cat-" + cur_cats[i]).removeClass("topic-filtered");
        }
        toggleFilters(null);
    }
}
function toggleTopic(id) {
    var toggler = $("#" + id);
    var cat = id.substring(8);
    var talks = $(".cat-" + cat);
    if (toggler.hasClass("catselected")) {
        toggler.removeClass("catselected");
        cur_cats = removeTopic(cat).split(",");
        for (i=0; i<cur_cats.length; i++) {
            talks = talks.not(".cat-" + cur_cats[i]);
        }
        talks.addClass("topic-filtered");
        if (topicFiltering()) {
            talks.hide();
            apply_striping();
        }
    } else {
        toggler.addClass("catselected");
        addTopic(cat);
        talks.removeClass("topic-filtered");
        if (topicFiltering()) {
            // elements may be filtered by other criteria
            talks = talksToShow(talks);
            talks.show();
            apply_striping();
        }
    }
}
function getAllTopics() {
    var toggles = []
    $(".topic_toggle").each(function() {
        toggles.push(this.id.substring(8));
    })
    return toggles;
}
function selectAllTopics() {
    var toggles = getAllTopics();
    setCookie("topics", toggles.join(","));
    $(".topic_toggle").addClass("catselected");
    var talks = $(".talk");
    talks.removeClass("topic-filtered");
    if (topicFiltering()) {
        talks = talksToShow(talks);
        talks.show();
        apply_striping();
    }
}
function clearAllTopics() {
    setCookie("topics", "");
    var toggles = getAllTopics();
    $(".topic_toggle").removeClass("catselected");
    var talks = $(".talk");
    talks.addClass("topic-filtered");
    if (topicFiltering()) {
        talks.hide();
        // no need to apply striping since no visible talks
    }
}

var filter_classes = [['.topic-filtered', topicFiltering], ['.calendar-filtered', calFiltering]]
function talksToShow(talks) {
    for (i=0; i<filter_classes.length; i++) {
        if (filter_classes[i][1]()) {
            talks = talks.not(filter_classes[i][0]);
        }
    }
    return talks;
}
function toggleFilters(id) {
    if (id !== null) {
        setCookie("filter_" + id.split("_")[1], $('#'+id).is(":checked") ? "1" : "0");
    }
    var talks = $('.talk');
    talks.hide();
    talks = talksToShow(talks);
    talks.show();
    apply_striping();
}

function apply_striping() {
    // Not sure if this gives the same order as $('.talk')
    var rows = $('#browse-talks tbody tr');
    rows.find('tr:visible').each(function(i) {
        if (i%2) {
            $(this).css('background', '#f7f7f7');
        } else {
            $(this).css('background', 'none');
        };
    });
}

function tickClock() {
    var curtime = $("#curtime").text();
    var hourmin = curtime.split(":");
    hourmin[1] = parseInt(hourmin[1]) + 1;
    if (hourmin[1] == 60) {
        hourmin[1] = 0;
        hourmin[0] = parseInt(hourmin[0]) + 1;
        if (hourmin[0] == 24) hourmin[0] = 0;
        hourmin[0] = hourmin[0].toString();
    }
    hourmin[1] = hourmin[1].toString().padStart(2, '0');
    curtime = hourmin.join(":");
    $("#curtime").text(curtime);
}

$(document).ready(function () {

    setTopicLinks();

    $('#timetoggle').click(
        function (evt) {
            evt.preventDefault();
            toggle_time();
            return false;
        });
    $('.topic_toggle').click(
        function (evt) {
            evt.preventDefault();
            toggleTopic(this.id);
        });

    var today = new Date();
    var minute = today.getMinutes();
    var millisecond = 1000 * today.getSeconds() + today.getMilliseconds();
    var displayed_minute = parseInt($("#curtime").text().split(":")[1]);
    console.log(displayed_minute);
    // We might have passed a minute barrier between the server setting the time and the page finishing loading
    // Because of weird time zones (the user time preference may not be their local clock time),
    // we only do something if the minute is offset by 1 or 2 (for a super-slow page load)
    if (minute == displayed_minute + 1) {
        tickClock();
    } else if (minute == displayed_minute + 2) {
        tickClock(); tickClock();
    }
    setTimeout(function() {
        tickClock();
        setInterval(function() {
            // update the clock in the top right every 60 seconds
        }, 60000);
    }, 60000 - millisecond);
});

$(document).ready(function() {

  var start = moment();
  var end = moment().add(6, 'days');
  var beginningoftime = '01/01/2020';
  var endoftime = '01/01/2050';



  $('input[name="daterange"]').on('cancel.daterangepicker', function(ev, picker) {
      $(this).val('');
  });

    $('#daterange').daterangepicker({
        startDate: start,
        endDate: end,
        autoUpdateInput: false,
        opens: "center",
        drops: "down",
        ranges: {
           'No restriction': [beginningoftime, endoftime],
           'Future': [moment(), endoftime],
           'Past': [beginningoftime, moment()],
           'Today': [moment(), moment()],
           'Next 7 Days': [moment(), moment().add(6, 'days')],
           'Next 30 Days': [moment(), moment().add(29, 'days')],
        },
      },
      function(start, end, label) {
      if(start.format('MM/DD/YYYY') == beginningoftime){
        start = '';
      } else {
        start = start.format('MMMM D, YYYY')
      }
      if(end.format('MM/DD/YYYY') == endoftime) {
        end = '';
      } else {
        end =  end.format('MMMM D, YYYY')
      }
      // everything is a string from now on
      if(start == "Invalid date") {
        start = ''
      }
      if(end == "Invalid date") {
        end = ''
      }
      if(start == '' && end == '') {
        $('#daterange').val('');
      } else {
        $('#daterange').val(start + ' - ' + end);
      }
    }
    );

    //cb(start, end);


});


function uniqueID(){
  function chr4(){
    return Math.random().toString(16).slice(-4);
  }
  return chr4() + chr4() +
    '-' + chr4() +
    '-' + chr4() +
    '-' + chr4() +
    '-' + chr4() + chr4() + chr4();
}

//handling subscriptions
$(document).ready(function(){
    function error(msg) {
      var id = uniqueID()
      var paragraph = document.createElement("p")
      paragraph.className = "error";
      var txt = document.createTextNode(msg);
      paragraph.appendChild(txt);
      paragraph.id = id;
      $('#flashes')[0].appendChild(paragraph);
      setTimeout(() => $('#'+id).fadeOut(1000), 2000)
    }
    function success(msg) {
      var id = uniqueID()
      var paragraph = document.createElement("p")
      paragraph.className = "message";
      var txt = document.createTextNode(msg);
      paragraph.appendChild(txt);
      paragraph.id = id;
      $('#flashes')[0].appendChild(paragraph);
      setTimeout(() => $('#'+id).fadeOut(1000), 2000)
    }

    $("input.subscribe:checkbox").change(function() {
        if($(this).is(":checked")) {
            $.ajax({
              url: '/user/subscribe/' +  $(this)[0].value,
              //success: success
            });
              console.log('/user/subscribe/' +  $(this)[0].value);
        } else {
          $.ajax({
            url: '/user/unsubscribe/' +  $(this)[0].value,
            //success: success
          });
            console.log('/user/unsubscribe/' +  $(this)[0].value);
        }
    });
});



function checkpw() {
  var match = "Too short";
  if($("#pw1").val().length < 8){
    "Too short (less than 8 characters)";
    $("#pw1status").html("Too short (less than 8 characters)");
    $("#pw2status").html("");
  } else {
    $("#pw1status").html("");
  }

  if($("#pw1").val() == $("#pw2").val()) {
    $("#pw2status").html("");
  } else {
    $("#pw2status").html("Not matching");
  }
}


