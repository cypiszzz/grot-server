'use strict';

// for debug purposes
var pr = console.log.bind(console);

var __isVisible = function() {
  return !Visibility || (Visibility && !Visibility.hidden());
};

var Synchronize = {

  RETRY: 1000,

  on: function(name, callback, context) {
    Backbone.Events.on.call(this, name, callback, context);

    if (name == 'sync' && !this._fetching) {
      this._fetch();
    }

    return this;
  },

  off: function(name, callback, context) {
    Backbone.Events.off.call(this, name, callback, context);

    if (!this._events['sync']) {
      this.__abortFetching();
    }

    return this;
  },

  __abortFetching: function() {
    if (this._fetching) {
      this._fetching.abort();
      this._fetching = null;
    }
  },

  __onHiddenListener: null,

  _fetch: function(options) {
    var _this = this;

    if (!__isVisible()) {
      var onceVisible = Visibility.onVisible(function() {
        _this._fetch(options);
        Visibility.unbind(onceVisible);
      });
      return;
    }

    if (this.__onHiddenListener === null) {
      this.__onHiddenListener = Visibility.change(function(orginalEvent, state) {
        if (state === 'hidden') {
          _this.__abortFetching();
        }
      });
    }

    options = _.extend(options || {}, {
      'ifModified': true,
      'success': function(model, response, options) {
        if (options.xhr.status == 200) {
          model._fetch();
        } else {
          model._fetching = null;

          _.delay(_.bind(model._fetch, model), Synchronize.RETRY * 15);
        }
      },
      'error': function(model, response, options) {
        _.delay(_.bind(model._fetch, model), Synchronize.RETRY);
      }
    });

    this._fetching = this.fetch(options);
  }
}

var Game = Backbone.Model.extend({
  urlRoot: '/games/',

  initialize: function(attributes, options) {
    this.players = new Players([], {
      'game': this
    });
    this.start_in = null;
    this.restart_in = null;
  },

  parse: function(response, options) {
    // not modified or empty
    if (_.isUndefined(response) || _.isEmpty(response)) {
      return this;
    }
    return response;
  }
});
_.extend(Game.prototype, Synchronize);

var Player = Backbone.Model.extend({

});
_.extend(Player.prototype, Synchronize);

var Players = Backbone.Collection.extend({
  model: Player,

  url: function() {
    return this.game.url() + '/players/';
  },

  comparator: function(player) {
    return -player.get('score');
  },

  initialize: function(models, options) {
    this.game = options.game;
  },

  parse: function(response, options) {
    // not modified
    if (_.isUndefined(response)) {
      return this.models;
    }

    // display last players if there is none waiting
    if (_.isEmpty(response.players)) {
      return this.models;
    }

    return response.players;
  }
});
_.extend(Players.prototype, Synchronize);

var ScoreBoard = Backbone.View.extend({
  template: _.template(
    '<li id="player_<%- player.id %>">' +
    '<div class="avatar"><img src="http://robohash.org/<%- player.name %>"></img></div>' +
    '<div class="position">-</div>' +
    '<div class="name"><%- player.name %></div>' +
    '<div class="moves"><%- player.moves %></div>' +
    '<div class="score"><%- player.score %></div>' +
    '</li>'
  ),

  initialize: function() {

    var _this = this;
    var topHeight = 65;
    var boardHeight;
    var $main = $('.main');

    this.listenTo(this.model.players, 'remove', this.remove);
    this.listenTo(this.model.players, 'sort', this.render);
    this.listenTo(this.model.players, 'sync', this.render);
    this.listenTo(this.model, 'sync', this.renderTimer);

    this.playerEntryHeight = 50;
    this.columnWidth = 400;
    $(window).on('resize', function() {
      boardHeight = $('body').height() - topHeight - 10;
      _this.playersInColumn = Math.floor((boardHeight - _this.playerEntryHeight - 20) / _this.playerEntryHeight);
      $main.css('height', boardHeight);
      _this.render();
    }).resize();
  },

  remove: function(model, collection, options) {
    this.$el.find('#player_' + model.id).remove();
  },

  renderTimer: function() {
    if (this.model.attributes.start_in !== null) {
      this.$el.find('#start_in').show();
      this.$el.find('#start_in span').text(this.model.attributes.start_in);
    } else {
      this.$el.find('#start_in').hide();
    }
    if (this.model.attributes.restart_in !== null) {
      this.$el.find('#restart_in').show();
      this.$el.find('#restart_in span').text(this.model.attributes.restart_in);
    } else {
      this.$el.find('#restart_in').hide();
    }
  },

  render: function() {
    for (var i = 0; i < this.model.players.models.length; i++) {

      var player = this.model.players.models[i].attributes;
      player.id = player.id.replace(' ', '_');
      var $playerEntry = this.$el.find('#player_' + player.id);

      if (!$playerEntry.get(0)) {
        $playerEntry = $(this.template({
          player: player
        }));
        this.$el.find('ul').append($playerEntry);
      }

      $playerEntry.find('.name').html(player.name);
      $playerEntry.find('.moves').html(player.moves);
      $playerEntry.find('.score').html(player.score);
      $playerEntry.find('.position').html(i + 1);

      var animate = {
        top: i * this.playerEntryHeight + this.playerEntryHeight + 20,
        left: 0
      };

      if (i + 1 > this.playersInColumn) {
        animate.left = '100%';
        animate.top -= (this.playersInColumn) * this.playerEntryHeight;
      }
      $playerEntry.stop(true).animate(animate, 300);
    }

    if (this.model.players.models.length < this.playersInColumn + 1) {
      this.$el.find('ul').removeClass('two-columns');
    } else {
      this.$el.find('ul').addClass('two-columns');
    }
  }
});

var PlayerBoard = Backbone.View.extend({
  template: _.template(
    '<table>' +
    '<% for (var x = 0; x < board.length; ++x) { %>' +
    '<tr>' +
    '<% for (var y = 0; y < board[x].length; ++y) { %>' +
    '<td><%- ARROWS[board[x][y].direction] %></td>' +
    '<% } %>' +
    '</tr>' +
    '<% } %>' +
    '</table>'
  ),

  initialize: function(options) {
    if (this.collection) {
      this.listenTo(this.collection, 'sync');
    }
  },

  show: function(model) {
    if (this.model) {
      this.stopListening(this.model);
    }

    this.model = model;

    if (this.model) {
      this.listenTo(this.model, 'change', this.render);
      this.listenTo(this.model, 'sync');
    }

    this.render();
  },

  render: function() {
    var ARROWS = {
      'up': '^',
      'down': 'v',
      'left': '<',
      'right': '>',
    };
    var board = this.model.get('board');

    this.$el.empty();
    this.$el.append($('<h3>').html('player:' + this.model.id + ' <small>points:' + this.model.get('score') + ' moves:' + this.model.get('moves') + '</small>'));
    this.$el.append($('<p>').text(this.model.get('moved')));

    if (board) {
      this.$el.append(this.template({
        'board': board,
        'ARROWS': ARROWS,
      }));
    }
  },
});
