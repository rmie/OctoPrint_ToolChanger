$(function() {
    function ToolChangerViewModel(parameters) {
        var self = this;
        var imagePort = $('#webcam_image');

        self.settings = parameters[0];
        self.tools = ko.observableArray();
        self.align = ko.observable(false);
        self.R1 = ko.observable(false);
        self.R2 = ko.observable(false);

        self.refresh = function() {
            uri = '/' + OctoPrint.getSimpleApiUrl('toolchanger') + '?apikey=' +  OctoPrint.options.apikey
            uri += '&image';
            uri += '&width=' + imagePort.width() + '&height=' + imagePort.height();
            uri += '&r1=' + self.R1() + '&r2=' + self.R2();
            imagePort.attr('src', uri);
        }

        self.R1.subscribe(self.refresh);
        self.R2.subscribe(self.refresh);

        self.align.subscribe(function() {
            if (self.align()) {
                self.current = imagePort.text()
                self.refresh();
            } else {
                imagePort.attr('src', self.current);
            }
        });
    };

    OCTOPRINT_VIEWMODELS.push([
        ToolChangerViewModel,
        ["settingsViewModel", "loginStateViewModel", "controlViewModel"],
        ["#tool_control"]
    ]);
});
