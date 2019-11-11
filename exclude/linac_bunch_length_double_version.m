%% Linac bunch length measurements
close all
clear all
dire = '/mxn/groups/operators/controlroom/robsva/MATLAB/Linac_bunch_length/data/';

% Camera to pull data from
cam = 'lima/liveviewer/i-bc2-dia-scrn-01';

% Number of pixels to average over
%pixX = 500; % Currently using the full horizontal width of the image
pixY = 280;

% mm per pixel on camera
mm_pix = 0.02396989381337041;

% Prepare data file dump
FileName = cat(2,dire,'BunchLength_',datestr(now,'yy-mm-dd_HH-MM-SS'),'.mat');
MeasData = struct([]);

bckg = load([dire 'bckg.mat']);



%% Manual version

% Degrees off crest in main linac
mainphase = 35;

% Conversion factor for bunch length
C = 0.32 * sind(mainphase)*2*pi*3e9;

% Get image
clearvars img
for i = 1:2
    img(:,:,i) = getfield(tango_read_attribute(cam, 'Image'), 'value') - bckg.img;
    pause(0.5)
end
img = mean(img, 3);

% Find the hottest pixels on the block
% Horizontal profile
xprof = sum(img, 1);
[v, xi] = max(xprof);
%xv = xi - pixX/2 : xi + pixX/2;
xv = 1:length(xprof);

% Vertical profile
yprof = sum(img, 2);
[v, yi] = max(yprof);
yv = yi - pixY/2 : yi + pixY/2;

% Average only the pulse
xprof = smooth( mean(img(yv, xv), 1), 7);
xprof = xprof - min(xprof);

% Fit gaussian profiles
[xf, gx] = fit(xv.', xprof, 'gauss1');

figure;plot(xf, xv, xprof)

xs = xf.c1 / sqrt(2);
xfwhm = 2.3548 * xs;    % FWHM = 2 * sqrt( 2 * log(2) ) * sigma
xfwhm2 = length(xprof((xprof > (max(xprof)/2))));   % Based on image data

% Calculate bunch length
xw_mm = mm_pix * xfwhm;
xw2_mm = mm_pix * xfwhm2;
xs_mm = mm_pix * xs;
xdt = (1e12 * xw_mm*1e-3) / C;
xdt2 = (1e12 * xw2_mm*1e-3) / C;
xdts = (1e12 * xs_mm*1e-3) / C;

% Save stuff
n = length(MeasData) + 1;

MeasData(n).degrees = mainphase;
MeasData(n).xprof = xprof;
MeasData(n).xi = xi;
MeasData(n).xf = xf;
MeasData(n).gx = gx;
MeasData(n).xs = xs;
MeasData(n).xfwhm = xfwhm;
MeasData(n).xfwhm2 = xfwhm2;
MeasData(n).xdt = xdt;
MeasData(n).xdt2 = xdt2;
MeasData(n).xdts = xdts;

%if exist(FileName,'file')
%    save(FileName, '-append','MeasData');
%else
%    save(FileName,'MeasData');
%end

fprintf('\n')
fprintf(['Degrees off crest: ' num2str(mainphase) ' deg.\n'])
fprintf(['FWHM (fit): ' num2str(MeasData(n).xfwhm) ' px\n']);
fprintf(['FWHM (data): ' num2str(MeasData(n).xfwhm2) ' px\n']);
fprintf(['Bunch length (FWHM fit): ' num2str(MeasData(n).xdt) ' ps\n']);
fprintf(['Bunch length (FWHM data): ' num2str(MeasData(n).xdt2) ' ps\n']);
fprintf(['Bunch length (sigma fit): ' num2str(MeasData(n).xdts) ' ps\n']);






% %% Change magnet version
% 
% % Magnet to change
% mag = 'I-KBC1/MAG/PSPA-01';
% magVec = 0.25:0.25:9.5;
% 
% % Number of pixels to average over
% pixX = 500;
% pixY = 120;
% 
% % mm per pixel on camera
% mm_pix = 0.02396989381337041;
% 
% % Degrees off crest in main linac
% mainphase = 30;
% 
% % Conversion factor for bunch length
% C = 0.32 * sind(mainphase)*2*pi*3e9;
% 
% % Prepare data file dump
% FileName = cat(2,dire,'BunchLength_',datestr(now,'yy-mm-dd_HH-MM-SS'),'.mat');
% MeasData = struct([]);
% 
% magStart = getfield(tango_read_attribute(mag, 'Current'), 'value', {1});
% bckg = load([dire 'bckg.mat']);
% 
% for n = 1:numel(magVec);
%     fprintf('Measurement: %d of %d, magnet current: %d A\n', n, numel(magVec), magVec(n))
%     tango_write_attribute(mag, 'Current', magVec(n))
%     pause(3)
% 
%     % Get image
%     for i = 1:5
%         img(:,:,i) = getfield(tango_read_attribute(cam, 'Image'), 'value') - bckg.img;
%         pause(0.5)
%     end
%     img = mean(img, 3);
%     
%     % Find the hottest pixels on the block
%     % Horizontal profile
%     xprof = sum(img, 1);
%     [v, xi] = max(xprof);
%     xv = xi - pixX/2 : xi + pixX/2;
%     
%     % Vertical profile
%     yprof = sum(img, 2);
%     [v, yi] = max(yprof);
%     yv = yi - pixY/2 : yi + pixY/2;
%     
%     % Average only the pulse
%     xprof = mean(img(yv, xv), 1);
%     
%     % Fit gaussian profiles
%     [xf, gx] = fit(xv.', xprof.', 'gauss1');
% 
%     figure;plot(xf, xv, xprof)
%     
%     xs = xf.c1 / sqrt(2);
%     xfwhm = 2.3548 * xs;    % FWHM = 2 * sqrt( 2 * log(2) ) * sigma
%     
%     % Calculate bunch length
%     xw_mm = mm_pix * xfwhm;
%     xs_mm = mm_pix * xs;
%     xdt = (1e12 * xw_mm*1e-3) / C;
%     xdts = (1e12 * xs_mm*1e-3) / C;
%     
%     % Save stuff
%     MeasData(n).xprof = xprof;
%     MeasData(n).xi = xi;
%     MeasData(n).xf = xf;
%     MeasData(n).gx = gx;
%     MeasData(n).xs = xs;
%     MeasData(n).xfwhm = xfwhm;
%     MeasData(n).xdt = xdt;
%     MeasData(n).xdts = xdts;
%     
%     
%     %{
%     % Average only the pulse
%     yprof = mean(img(yv, xv), 2)';
%     
%     % Fit gaussian profiles
%     [yf, gy] = fit(yv.', yprof.', 'gauss1');
% 
%     ys = yf.c1 / sqrt(2);
%     yfwhm = 2.3548 * ys;
%     
%     yw_mm = mm_pix * yfwhm;
%     ysig_mm = mm_pix * ys;
% 
%     MeasData(n).yprof = yprof;
%     MeasData(n).yi = yi;
%     MeasData(n).yf = yf;
%     MeasData(n).gy = gy;
%     MeasData(n).ys = ys;
%     MeasData(n).yfwhm = yfwhm;
%     
%     MeasData(n).magnet = mag;
%     MeasData(n).current = magVec(n);
%     %} 
%     
%     
%     if exist(FileName,'file')
%         save(FileName, '-append','MeasData');
%     else
%         save(FileName,'MeasData');
%     end
%     
%     pause(0.5)
% 
% end
% 
% % Restore magnet to initial value
% tango_write_attribute(mag, 'Current', magStart)
% 
% % Gauss1
% %xf(x) =  a1*exp(-((x-b1)/c1)^2)
% 
% % Plot FWHM
% %MeasX = cat(1, MeasData.xfwhm);
% MeasX = cat(1, MeasData.xdt);
% figure;
% plot(magVec, MeasX)
% title('Horizontal')
% xlabel('Magnet current [A]')
% ylabel('FWHM')
% grid on
% 
% %{
% MeasY = cat(1, MeasData.yfwhm);
% figure;
% plot(magVec, MeasY)
% title('Vertical')
% xlabel('Magnet current [A]')
% ylabel('FWHM')
% grid on
% %}
% 
% 
