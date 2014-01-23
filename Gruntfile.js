module.exports = function(grunt) {
  var pkg = grunt.file.readJSON('package.json');

  grunt.loadNpmTasks('grunt-contrib-uglify');
  grunt.loadNpmTasks('grunt-contrib-less');
  grunt.loadNpmTasks('grunt-contrib-imagemin');
  grunt.loadNpmTasks('grunt-contrib-copy');
  grunt.loadNpmTasks('grunt-contrib-watch');
  grunt.loadNpmTasks('grunt-contrib-coffee');

  // Change relative directory
  grunt.file.setBase('ckanext/ga_report/');

  // Project configuration.
  grunt.initConfig({
    pkg: pkg,
    less: {
      options: {
        yuicompress: true
      },
      build: {
        files: { 'public/css/ga_d3.min.css' : 'public_src/less/ga_d3.less' }
      }
    },
    watch: {
      less: {
        files: 'public_src/less/**/*',
        tasks: 'less'
      },
      coffee: {
        files: 'public_src/coffee/**/*',
        tasks: 'coffee'
      }
    },
    coffee: {
      ga_reports: {
        src: [
          'public_src/coffee/**/*.coffee',
        ],
        dest: 'public/scripts/ga_d3_pack.min.js'
      }
    }
  });

  // Default task(s).
  grunt.registerTask('default', ['coffee','less']);
};
