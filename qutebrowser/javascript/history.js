/**
 * Copyright 2017 Imran Sobir
 *
 * This file is part of qutebrowser.
 *
 * qutebrowser is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * qutebrowser is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.
 */

"use strict";

window.loadHistory = (function() {
    // Date of last seen item.
    var lastItemDate = null;

    // Each request for new items includes the time of the last item and an
    // offset. The offset is equal to the number of items from the previous
    // request that had time=nextTime, and causes the next request to skip
    // those items to avoid duplicates.
    var nextTime = null;
    var nextOffset = 0;

    // The URL to fetch data from.
    var DATA_URL = "qute://history/data";

    // Various fixed elements
    var EOF_MESSAGE = document.getElementById("eof");
    var LOAD_LINK = document.getElementById("load");
    var HIST_CONTAINER = document.getElementById("hist-container");

    /**
     * Finds or creates the session table>tbody to which item with given date
     * should be added.
     *
     * @param {Date} date - the date of the item being added.
     * @returns {Element} the element to which new rows should be added.
     */
    function getSessionNode(date) {
        // Find/create table
        var tableId = ["hist", date.getDate(), date.getMonth(),
            date.getYear()].join("-");
        var table = document.getElementById(tableId);
        if (table === null) {
            table = document.createElement("table");
            table.id = tableId;

            // Caption contains human-readable date
            var caption = document.createElement("caption");
            caption.className = "date";
            var options = {
                "weekday": "long",
                "year": "numeric",
                "month": "long",
                "day": "numeric",
            };
            caption.innerHTML = date.toLocaleDateString("en-US", options);
            table.appendChild(caption);

            // Add table to page
            HIST_CONTAINER.appendChild(table);
        }

        // Find/create tbody
        var tbody = table.lastChild;
        if (tbody.tagName !== "TBODY") {
            tbody = document.createElement("tbody");
            table.appendChild(tbody);
        }

        // Create session-separator and new tbody if necessary
        if (tbody.lastChild !== null && lastItemDate !== null &&
                window.SESSION_INTERVAL > 0) {
            var interval = lastItemDate.getTime() - date.getTime();
            if (interval > window.SESSION_INTERVAL) {
                // Add session-separator
                var sessionSeparator = document.createElement("td");
                sessionSeparator.className = "session-separator";
                sessionSeparator.colSpan = 2;
                sessionSeparator.innerHTML = "&#167;";
                table.appendChild(document.createElement("tr"));
                table.lastChild.appendChild(sessionSeparator);

                // Create new tbody
                tbody = document.createElement("tbody");
                table.appendChild(tbody);
            }
        }

        return tbody;
    }

    /**
     * Given a history item, create and return <tr> for it.
     *
     * @param {string} itemUrl - The url for this item.
     * @param {string} itemTitle - The title for this item.
     * @param {string} itemTime - The formatted time for this item.
     * @returns {Element} the completed tr.
     */
    function makeHistoryRow(itemUrl, itemTitle, itemTime) {
        var row = document.createElement("tr");

        var title = document.createElement("td");
        title.className = "title";
        var link = document.createElement("a");
        link.href = itemUrl;
        link.innerHTML = itemTitle;
        var host = document.createElement("span");
        host.className = "hostname";
        host.innerHTML = link.hostname;
        title.appendChild(link);
        title.appendChild(host);

        var time = document.createElement("td");
        time.className = "time";
        time.innerHTML = itemTime;

        row.appendChild(title);
        row.appendChild(time);

        return row;
    }

    /**
     * Get JSON from given URL.
     *
     * @param {string} url - the url to fetch data from.
     * @param {function} callback - the function to callback with data.
     * @returns {void}
     */
    function getJSON(url, callback) {
        var xhr = new XMLHttpRequest();
        xhr.open("GET", url, true);
        xhr.responseType = "json";
        xhr.onload = function() {
            var status = xhr.status;
            callback(status, xhr.response);
        };
        xhr.send();
    }

    /**
     * Receive history data from qute://history/data.
     *
     * @param {Number} status - The status of the query.
     * @param {Array} history - History data.
     * @returns {void}
     */
    function receiveHistory(status, history) {
        if (history === null) {
            return;
        }

        if (history.length === 0) {
            // Reached end of history
            window.onscroll = null;
            EOF_MESSAGE.style.display = "block";
            LOAD_LINK.style.display = "none";
            return;
        }

        nextTime = history[history.length - 1].time;
        nextOffset = 0;

        for (var i = 0, len = history.length; i < len; i++) {
            var item = history[i];
            // python's time.time returns seconds, but js Date expects ms
            var currentItemDate = new Date(item.time * 1000);
            getSessionNode(currentItemDate).appendChild(makeHistoryRow(
                item.url, item.title, currentItemDate.toLocaleTimeString()
            ));
            lastItemDate = currentItemDate;
            if (item.time === nextTime) {
                nextOffset++;
            }
        }
    }

    /**
     * Load new history.
     * @return {void}
     */
    function loadHistory() {
        var url = DATA_URL.concat("?offset=", nextOffset.toString());
        if (nextTime === null) {
            getJSON(url, receiveHistory);
        } else {
            url = url.concat("&start_time=", nextTime.toString());
            getJSON(url, receiveHistory);
        }
    }

    return loadHistory;
})();
