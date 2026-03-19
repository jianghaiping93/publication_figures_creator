function apply_matlab_style()
% Unified MATLAB style preset aligned with docs/style_config.yaml.
theme = getenv('PFC_STYLE_THEME');
theme = lower(strrep(theme, '-', '_'));
set(groot, 'DefaultFigureColor', 'w');
set(groot, 'DefaultAxesFontName', 'Source Sans 3');
set(groot, 'DefaultAxesFontSize', 9);
set(groot, 'DefaultTextFontSize', 9);
set(groot, 'DefaultLineLineWidth', 1.0);
set(groot, 'DefaultAxesColorOrder', categorical_palette(theme));
end

function colors = categorical_palette(theme)
if nargin < 1 || isempty(theme)
    theme = 'classic';
end
switch theme
    case 'mono_ink'
        colors = [
            0.067 0.067 0.067;
            0.200 0.200 0.200;
            0.333 0.333 0.333;
            0.467 0.467 0.467;
            0.600 0.600 0.600;
            0.733 0.733 0.733;
        ];
    case 'ocean'
        colors = [
            0.000 0.247 0.361;
            0.184 0.294 0.486;
            0.400 0.318 0.569;
            0.000 0.651 0.839;
            0.302 0.616 0.878;
            0.627 0.769 1.000;
        ];
    case 'forest'
        colors = [
            0.106 0.263 0.196;
            0.176 0.416 0.310;
            0.251 0.569 0.424;
            0.322 0.718 0.533;
            0.455 0.776 0.616;
            0.584 0.835 0.698;
        ];
    case 'solar'
        colors = [
            0.498 0.310 0.141;
            0.690 0.537 0.408;
            0.902 0.722 0.635;
            0.867 0.722 0.573;
            0.996 0.980 0.878;
            0.737 0.424 0.145;
        ];
    otherwise
        colors = [
            0.298 0.471 0.659;  % #4C78A8
            0.961 0.522 0.094;  % #F58518
            0.329 0.643 0.294;  % #54A24B
            0.894 0.341 0.337;  % #E45756
            0.447 0.718 0.698;  % #72B7B2
            0.698 0.475 0.635;  % #B279A2
            1.000 0.616 0.651;  % #FF9DA6
            0.616 0.459 0.365;  % #9D755D
            0.729 0.690 0.675;  % #BAB0AC
        ];
end
end
