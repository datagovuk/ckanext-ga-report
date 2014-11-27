try:
    # optional fancy progress bar you can install
    from progressbar import ProgressBar, Percentage, Bar, ETA

    class GaProgressBar(ProgressBar):
        def __init__(self, total):
            if total == 0:
                return
            widgets = ['Test: ', Percentage(), ' ', Bar(),
                       ' ', ETA(), ' ']
            ProgressBar.__init__(self, widgets=widgets,
                                 maxval=total)
            self.start()

except ImportError:
    class GaProgressBar(object):
        def __init__(self, total):
            self.total = total

        def update(self, count):
            if count % 100 == 0:
                print '.. %d/%d done so far' % (count, self.total)
