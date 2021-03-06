$('#submit-key').click(function (e) {
    submitkey($('#chalid').val(), $('#answer').val())
});

$('#submit-keys').click(function (e) {
    e.preventDefault();
    $('#update-keys').modal('hide');
});

function loadchal(id, update) {
    $.get(script_root + '/admin/chal/' + id, function (obj) {
        $('#desc-write-link').click(); // Switch to Write tab
        if (typeof update === 'undefined')
            $('#update-challenge').modal();
    });
}

function openchal(id) {
    loadchal(id);
}

function reset() {

}

$(document).ready(function () {
    $('[data-toggle="tooltip"]').tooltip();
    $("#reset-cases").click(function (e) {
        var row = $(this)
            .parent()
            .parent();
        ezq({
            title: "Delete Files",
            body: "清空所有测试数据",
            success: function () {
                CTFd.fetch("/api/v1/cases/" + CHALLENGE_ID, {
                    method: "DELETE"
                })
                    .then(function (response) {
                        return response.json();
                    })
                    .then(function (response) {
                        if (response.success) {
                            row.remove();
                        }
                    });
            }
        });
    });
    $('#cases-form').submit(function (e) {
        e.preventDefault();
        var formData = new FormData(e.target);
        formData.append("nonce", csrf_nonce);
        var pg = ezpg({
            width: 0,
            title: "Upload Progress"
        });
        $.ajax({
            url: script_root + "/api/v1/cases/" + CHALLENGE_ID,
            data: formData,
            type: "POST",
            cache: false,
            contentType: false,
            processData: false,
            xhr: function () {
                var xhr = $.ajaxSettings.xhr();
                xhr.upload.onprogress = function (e) {
                    if (e.lengthComputable) {
                        var width = (e.loaded / e.total) * 100;
                        pg = ezpg({
                            target: pg,
                            width: width
                        });
                    }
                };
                return xhr;
            },
            success: function (data) {
                e.target.reset();

                pg = ezpg({
                    target: pg,
                    width: 100
                });
                setTimeout(function () {
                    pg.modal("hide");
                }, 500);

                setTimeout(function () {
                    window.location.reload();
                }, 700);
            }
        });
    })
});
